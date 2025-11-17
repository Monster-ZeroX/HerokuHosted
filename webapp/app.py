"""
Flask web application for Torrent to Google Drive.
"""
import os
import re
import json
import requests
import asyncio
from uuid import uuid4
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from typing import Optional
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from markupsafe import Markup
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

from webapp.models import db, User, Torrent, TorrentFile, InviteCode, PaymentTransaction, init_db
from webapp.torrent_search import search_torrents
from torrent import TorrentClient, format_size
from drive import RcloneManager
from config import settings
from mega_downloader import MegaDownloader

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///torrents.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
allowed_origins = set(filter(None, os.environ.get('ALLOWED_ORIGINS', '').split(',')))

GENIE_API_KEY = os.environ.get('GENIE_API_KEY')
GENIE_MERCHANT_ID = os.environ.get('GENIE_MERCHANT_ID')
GENIE_API_BASE = os.environ.get('GENIE_API_BASE', 'https://api.geniebiz.lk/public/v2')
GENIE_CURRENCY = os.environ.get('GENIE_CURRENCY', 'LKR')
GENIE_CREATE_PAYMENT_URL = os.environ.get('GENIE_CREATE_PAYMENT_URL')
GENIE_PAYMENT_STATUS_URL = os.environ.get('GENIE_PAYMENT_STATUS_URL')

def _gb_to_bytes(gb: float) -> int:
    return int(gb * (1024 ** 3))


PAID_PLANS = {
    'plus100': {
        'label': '100GB / day',
        'price': float(os.environ.get('PLAN_100_PRICE_LKR', '300')),
        'limit_bytes': _gb_to_bytes(100),
    },
    'plus300': {
        'label': '300GB / day',
        'price': float(os.environ.get('PLAN_300_PRICE_LKR', '600')),
        'limit_bytes': _gb_to_bytes(300),
    },
    'unlimited': {
        'label': 'Unlimited per day',
        'price': float(os.environ.get('PLAN_UNLIMITED_PRICE_LKR', '1200')),
        'limit_bytes': 0,
    },
}

# Initialize database
init_db(app)


def format_eta(seconds):
    """Convert seconds to human readable ETA."""
    if seconds is None or seconds < 0:
        return None
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"


@app.context_processor
def inject_formatters():
    return {
        'format_size': format_size,
        'format_eta': format_eta
    }


def build_payment_urls():
    base = GENIE_API_BASE.rstrip('/')
    create_url = GENIE_CREATE_PAYMENT_URL or f"{base}/transactions"
    status_url_template = GENIE_PAYMENT_STATUS_URL or f"{base}/transactions/{{payment_id}}"
    return create_url, status_url_template


def _genie_headers():
    if not GENIE_API_KEY:
        return None
    token = GENIE_API_KEY.strip()
    # Some Genie environments expect the raw API key (no Bearer prefix), while others
    # require an explicit scheme. Respect whatever was provided.
    if re.match(r"^(bearer|basic)\s", token, re.IGNORECASE):
        auth_value = token
    else:
        auth_value = token
    return {
        'Authorization': auth_value,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }


def extract_payment_url(response_json: dict):
    """Return the best available checkout URL from Genie."""
    if not response_json:
        return None
    for key in ('payment_url', 'redirectUrl', 'checkoutUrl', 'url'):
        if response_json.get(key):
            return response_json.get(key)
    data = response_json.get('data') or {}
    for key in ('payment_url', 'redirectUrl', 'checkoutUrl', 'url'):
        if data.get(key):
            return data.get(key)
    return None


def create_payment_session(user: User, plan_key: str, txn: PaymentTransaction) -> tuple[Optional[str], Optional[str]]:
    """Create a Genie payment session and return (payment_url, gateway_payment_id)."""
    headers = _genie_headers()
    if not headers:
        return None, None

    plan = PAID_PLANS.get(plan_key)
    create_url, _ = build_payment_urls()
    payload = {
        # The public v2 transactions endpoint expects only core payment fields. Supplying
        # optional identifiers like merchantId/reference/callbackUrl triggers a 400 with
        # "property ... should not exist", so stick to the minimal contract.
        #
        # Genie treats the amount value as cents, so convert LKR rupees to cents to avoid
        # showing "Rs 3" instead of "Rs 300" for a 300 LKR plan.
        'amount': int(plan['price'] * 100),
        'currency': GENIE_CURRENCY,
    }
    # Keep a local correlation ID when allowed without violating the schema. If Genie
    # rejects this field it will surface in the error log and can be removed quickly.
    if txn.reference:
        payload['localId'] = txn.reference

    try:
        response = requests.post(create_url, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
        payment_url = extract_payment_url(data)
        gateway_id = data.get('payment_id') or data.get('id') or (data.get('data') or {}).get('id')
        return payment_url, gateway_id
    except Exception as exc:
        body = None
        try:
            body = response.text  # type: ignore[name-defined]
        except Exception:
            pass
        app.logger.error(f"Genie payment creation failed: {exc}{f' | response={body}' if body else ''}")
        return None, None


def fetch_payment_status(payment_id: str) -> Optional[str]:
    """Fetch payment status from Genie (returns paid/pending/failed).

    Genie can return either `status` or `state` depending on the endpoint and environment.
    Normalise both so we can reliably decide when to upgrade a user.
    """
    headers = _genie_headers()
    if not headers or not payment_id:
        return None

    _, status_url_template = build_payment_urls()
    status_url = status_url_template.format(payment_id=payment_id)

    try:
        response = requests.get(status_url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json() or {}

        # Genie uses `state` (e.g., COMPLETED) in many responses; `status` may also appear
        # in some environments. Prefer state, then status, and normalise to lower case.
        state = data.get('state') or (data.get('data') or {}).get('state') or (data.get('transaction') or {}).get('state')
        status = data.get('status') or (data.get('data') or {}).get('status') or (data.get('transaction') or {}).get('status')

        normalized = None
        for candidate in (state, status):
            if isinstance(candidate, str) and candidate.strip():
                normalized = candidate.strip().lower()
                break

        if not normalized:
            return None

        if normalized in ('completed', 'paid', 'success', 'succeeded', 'confirmed', 'approved'):
            return 'paid'
        if normalized in ('failed', 'canceled', 'cancelled', 'declined', 'voided', 'rejected'):
            return 'failed'
        return 'pending'
    except Exception as exc:
        app.logger.error(f"Failed to verify payment status: {exc}")
        return None


def refresh_pending_transactions(user: User):
    """Recheck any pending Genie payments for the user and apply upgrades when paid."""
    pending = PaymentTransaction.query.filter_by(user_id=user.id, status='pending').all()
    updated = False
    for txn in pending:
        if not txn.gateway_payment_id:
            continue
        status = fetch_payment_status(txn.gateway_payment_id)
        if status == 'paid':
            txn.mark_paid()
            apply_paid_plan(txn.user, txn.plan_key)
            updated = True
        elif status == 'failed':
            txn.mark_failed('gateway_failed')
    if updated:
        db.session.commit()


def _attach_gateway_response(txn: PaymentTransaction, payload: dict):
    """Store raw gateway payload for auditing without breaking existing data."""
    if not payload:
        return
    try:
        existing = json.loads(txn.raw_response) if txn.raw_response else {}
    except Exception:
        existing = {}
    merged = {**existing, 'last_webhook': payload}
    txn.raw_response = json.dumps(merged)


def apply_paid_plan(user: User, plan_key: str):
    plan = PAID_PLANS.get(plan_key)
    if not plan:
        return False

    if user.base_daily_limit is None:
        user.base_daily_limit = user.daily_limit or 0

    user.apply_subscription(plan_key, plan['limit_bytes'])
    return True


def extract_submission_metadata(source_path: str):
    """Best-effort extraction of torrent name and hash without waiting on DHT."""
    name = None
    info_hash = None
    total_size = None

    try:
        if source_path.startswith('magnet:'):
            parsed = urlparse(source_path)
            params = parse_qs(parsed.query)

            dn_values = params.get('dn', [])
            if dn_values:
                name = dn_values[0]

            xt_values = params.get('xt', [])
            for xt in xt_values:
                if xt.startswith('urn:btih:'):
                    info_hash = xt.split(':')[-1].upper()
                    break
        elif source_path and os.path.exists(source_path):
            try:
                import libtorrent as lt

                ti = lt.torrent_info(source_path)
                name = ti.name()
                info_hash = str(ti.info_hash())
                total_size = ti.total_size()
            except Exception as e:
                app.logger.warning(f"Failed to parse torrent file metadata: {e}")
    except Exception as e:
        app.logger.warning(f"Metadata extraction fallback failed: {e}")

    return name, info_hash, total_size


@app.after_request
def add_cors_headers(response):
    """Allow the Next.js frontend to communicate with the API using cookies."""
    origin = request.headers.get('Origin')
    if origin and (not allowed_origins or origin in allowed_origins):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Vary'] = 'Origin'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@app.before_request
def refresh_subscription_state():
    if current_user.is_authenticated:
        current_user.ensure_subscription_is_current()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Authentication Routes
@app.route('/')
def index():
    """Home page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


def require_api_auth():
    """Guard API endpoints and return a JSON 401 instead of redirect."""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 401
    return None


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        invite_code = request.form.get('invite_code')

        # Validate input
        if not username or not password or not invite_code:
            flash('All fields are required', 'danger')
            return render_template('register.html')

        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('register.html')

        # Validate invite code
        invite = InviteCode.query.filter_by(code=invite_code).first()
        if not invite or not invite.is_valid():
            flash('Invalid or expired invite code', 'danger')
            return render_template('register.html')

        # Create user
        user = User(username=username)
        user.set_password(password)

        # Apply download limit from invite code
        if invite.daily_download_limit:
            user.daily_limit = invite.daily_download_limit
            user.base_daily_limit = invite.daily_download_limit
        else:
            user.base_daily_limit = 0

        db.session.add(user)

        # Use invite code
        invite.use()

        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()

            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')


@app.route('/api/login', methods=['POST'])
def api_login():
    """JSON-friendly login endpoint for the Next.js frontend."""
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        login_user(user, remember=True)
        user.last_login = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'is_admin': user.is_admin
            }
        })

    return jsonify({'error': 'Invalid credentials'}), 401


@app.route('/api/logout', methods=['POST'])
def api_logout():
    if not current_user.is_authenticated:
        return jsonify({'message': 'Already logged out'})
    logout_user()
    return jsonify({'message': 'Logged out'})


def serialize_torrent(torrent: Torrent, include_files: bool = False, include_tmdb: bool = False):
    data = {
        'id': torrent.id,
        'name': torrent.name,
        'status': torrent.status,
        'progress': torrent.progress,
        'download_rate': torrent.download_rate,
        'eta_seconds': torrent.eta_seconds,
        'gdrive_link': torrent.gdrive_link,
        'index_link': torrent.index_link,
        'selection_mode': torrent.selection_mode,
        'selected_file_indices': torrent.selected_file_indices,
        'created_at': torrent.created_at.isoformat() if torrent.created_at else None,
        'completed_at': torrent.completed_at.isoformat() if torrent.completed_at else None,
        'total_size': torrent.total_size,
        'error_message': torrent.error_message
    }

    if include_files:
        data['files'] = [
            {
                'id': f.id,
                'file_path': f.file_path,
                'file_size': f.file_size,
                'index_link': f.index_link,
                'gdrive_link': f.gdrive_link,
            }
            for f in torrent.files
        ]

    if include_tmdb:
        tmdb_query = guess_movie_title(torrent)
        tmdb_info = get_tmdb_movie_details(tmdb_query) if tmdb_query else None
        data['tmdb'] = tmdb_info

    return data


@app.route('/api/me')
def api_me():
    auth_error = require_api_auth()
    if auth_error:
        return auth_error

    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'is_admin': current_user.is_admin,
        'daily_limit_gb': current_user.get_daily_limit_gb(),
        'daily_usage_gb': current_user.get_daily_usage_gb(),
        'total_usage_gb': current_user.get_total_usage_gb(),
        'subscription_plan': current_user.subscription_plan,
        'subscription_expires_at': current_user.subscription_expires_at.isoformat() if current_user.subscription_expires_at else None,
    })


@app.route('/api/torrents')
def api_torrents():
    auth_error = require_api_auth()
    if auth_error:
        return auth_error

    torrents = Torrent.query.filter_by(user_id=current_user.id).order_by(Torrent.created_at.desc()).all()
    return jsonify([serialize_torrent(t) for t in torrents])


@app.route('/api/torrents/<int:torrent_id>')
def api_torrent_detail(torrent_id):
    auth_error = require_api_auth()
    if auth_error:
        return auth_error

    torrent = Torrent.query.get_or_404(torrent_id)
    if torrent.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403

    return jsonify(serialize_torrent(torrent, include_files=True, include_tmdb=True))


@app.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    return redirect(url_for('index'))


@app.route('/upgrade')
@login_required
def upgrade():
    current_user.reset_daily_usage_if_needed()
    refresh_pending_transactions(current_user)

    recent_txns = PaymentTransaction.query.filter_by(user_id=current_user.id).order_by(
        PaymentTransaction.created_at.desc()
    ).limit(10).all()

    plan_context = {
        key: {
            **details,
            'price_display': f"{GENIE_CURRENCY} {details['price']:.0f} / 30 days",
            'limit_gb': None if details['limit_bytes'] == 0 else round(details['limit_bytes'] / (1024 ** 3)),
        }
        for key, details in PAID_PLANS.items()
    }

    return render_template(
        'upgrade.html',
        plans=plan_context,
        currency=GENIE_CURRENCY,
        gateway_ready=bool(GENIE_API_KEY and GENIE_MERCHANT_ID),
        current_plan=current_user.subscription_plan,
        expires_at=current_user.subscription_expires_at,
        base_limit_gb=current_user.base_daily_limit / (1024 ** 3) if current_user.base_daily_limit else None,
        current_limit_gb=current_user.get_daily_limit_gb(),
        recent_txns=recent_txns,
    )


@app.route('/upgrade/start', methods=['POST'])
@login_required
def start_upgrade():
    plan_key = request.form.get('plan')
    plan = PAID_PLANS.get(plan_key)

    if not plan:
        flash('Invalid plan selected', 'danger')
        return redirect(url_for('upgrade'))

    # Prevent double-purchase of the same active plan
    if current_user.subscription_plan == plan_key and current_user.subscription_expires_at and current_user.subscription_expires_at > datetime.utcnow():
        flash('You already have this plan active.', 'info')
        return redirect(url_for('upgrade'))

    reference = f"txn_{uuid4().hex}"
    txn = PaymentTransaction(
        user_id=current_user.id,
        plan_key=plan_key,
        amount_cents=int(plan['price'] * 100),
        currency=GENIE_CURRENCY,
        reference=reference,
    )
    db.session.add(txn)
    db.session.commit()

    payment_url, gateway_id = create_payment_session(current_user, plan_key, txn)
    if gateway_id:
        txn.gateway_payment_id = gateway_id
        db.session.commit()

    if payment_url:
        return render_template(
            'upgrade_checkout.html',
            payment_url=payment_url,
            txn=txn,
            plan=plan,
            currency=GENIE_CURRENCY,
        )

    flash('Unable to start payment. Please check Genie API settings.', 'danger')
    txn.mark_failed('payment_url_missing')
    return redirect(url_for('upgrade'))


@app.route('/upgrade/confirm')
@login_required
def upgrade_confirm():
    txn_id = request.args.get('txn')
    payment_id = request.args.get('payment_id')

    txn = PaymentTransaction.query.get_or_404(txn_id) if txn_id else None
    if not txn:
        flash('Payment not found.', 'danger')
        return redirect(url_for('upgrade'))

    if txn.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to view this payment.', 'danger')
        return redirect(url_for('dashboard'))

    if payment_id and not txn.gateway_payment_id:
        txn.gateway_payment_id = payment_id
        db.session.commit()

    # If a webhook already confirmed payment, apply and exit early
    if txn.status == 'paid':
        apply_paid_plan(current_user, txn.plan_key)
        flash('Payment received! Your plan has been upgraded.', 'success')
        return redirect(url_for('dashboard'))

    status = fetch_payment_status(txn.gateway_payment_id or payment_id)
    if status == 'paid':
        txn.mark_paid()
        apply_paid_plan(current_user, txn.plan_key)
        flash('Payment received! Your plan has been upgraded.', 'success')
        return redirect(url_for('dashboard'))

    if status == 'failed':
        txn.mark_failed(f"status={status}")
        flash('Payment failed or was canceled.', 'danger')
        return redirect(url_for('upgrade'))

    flash('Payment is still pending. We will upgrade you automatically once it clears.', 'info')
    return redirect(url_for('upgrade'))


@app.route('/api/payments/<reference>/status')
@login_required
def api_payment_status(reference):
    txn = PaymentTransaction.query.filter_by(reference=reference).first_or_404()
    if txn.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'forbidden'}), 403

    status = txn.status
    if status == 'pending' and txn.gateway_payment_id:
        refreshed = fetch_payment_status(txn.gateway_payment_id)
        if refreshed == 'paid':
            txn.mark_paid()
            apply_paid_plan(txn.user, txn.plan_key)
            status = 'paid'
        elif refreshed == 'failed':
            txn.mark_failed('gateway_failed')
            status = 'failed'

    return jsonify({
        'status': status,
        'plan': txn.plan_key,
        'payment_id': txn.gateway_payment_id,
        'reference': txn.reference,
        'expires_at': txn.user.subscription_expires_at.isoformat() if txn.user.subscription_expires_at else None,
    })


# Dashboard Routes
@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    # Reset daily usage if needed
    current_user.reset_daily_usage_if_needed()
    refresh_pending_transactions(current_user)

    torrents = Torrent.query.filter_by(user_id=current_user.id).order_by(Torrent.created_at.desc()).all()

    # Calculate usage stats
    usage_stats = {
        'daily_usage_gb': current_user.get_daily_usage_gb(),
        'total_usage_gb': current_user.get_total_usage_gb(),
        'daily_limit_gb': current_user.get_daily_limit_gb(),
        'remaining_quota_gb': current_user.get_remaining_quota_gb(),
        'has_limit': current_user.daily_limit > 0 if current_user.daily_limit else False
    }

    subscription_info = None
    if current_user.subscription_plan and current_user.subscription_expires_at:
        remaining = current_user.subscription_expires_at - datetime.utcnow()
        if remaining.total_seconds() > 0:
            plan_details = PAID_PLANS.get(current_user.subscription_plan, {})
            subscription_info = {
                'label': plan_details.get('label', current_user.subscription_plan),
                'expires_at': current_user.subscription_expires_at,
                'days_left': remaining.days,
                'hours_left': int((remaining.total_seconds() % 86400) // 3600),
            }

    return render_template('dashboard.html', torrents=torrents, usage_stats=usage_stats, subscription_info=subscription_info)


@app.route('/add-torrent', methods=['GET', 'POST'])
@login_required
def add_torrent():
    """Add new torrent with optional file selection."""

    magnet_link = (request.values.get('magnet_link') or '').strip()
    selection_mode = request.values.get('selection_mode', 'all')
    uploaded_file_path = request.values.get('uploaded_file_path', '')
    torrent_files = []
    torrent_name = None
    total_size = None

    if request.method == 'POST':
        step = request.form.get('step', 'input')
        selection_mode = request.form.get('selection_mode', selection_mode)
        magnet_link = (request.form.get('magnet_link') or magnet_link).strip()
        uploaded_file_path = request.form.get('uploaded_file_path', uploaded_file_path)

        torrent_file = request.files.get('torrent_file')
        source_path = None

        # Persist uploaded torrent files for later processing
        if torrent_file and torrent_file.filename:
            upload_dir = Path(settings.DOWNLOAD_DIR) / 'uploads'
            upload_dir.mkdir(parents=True, exist_ok=True)
            filename = secure_filename(torrent_file.filename) or f'{uuid4().hex}.torrent'
            saved_path = upload_dir / f"{uuid4().hex}_{filename}"
            torrent_file.save(saved_path)
            source_path = str(saved_path)
            uploaded_file_path = source_path
        elif uploaded_file_path:
            source_path = uploaded_file_path
        else:
            source_path = magnet_link

        if not source_path:
            flash('Please provide a magnet link or .torrent file', 'danger')
            return render_template(
                'add_torrent.html',
                selection_mode=selection_mode,
                magnet_link=magnet_link,
                uploaded_file_path=uploaded_file_path
            )

        if not source_path.startswith('magnet:') and not Path(source_path).exists():
            flash('Invalid torrent input. Provide a magnet link or upload a .torrent file.', 'danger')
            return render_template(
                'add_torrent.html',
                selection_mode=selection_mode,
                magnet_link=magnet_link,
                uploaded_file_path=uploaded_file_path
            )

        # Step 1: Allow users to preview and select files
        if selection_mode == 'select' and step == 'input':
            try:
                torrent_client = TorrentClient()
                torrent_info = asyncio.run(torrent_client.get_torrent_info(source_path))
                torrent_files = torrent_info.files
                torrent_name = torrent_info.name
                total_size = torrent_info.total_size

                return render_template(
                    'add_torrent.html',
                    selection_mode=selection_mode,
                    magnet_link=magnet_link if source_path.startswith('magnet:') else '',
                    uploaded_file_path=source_path if not source_path.startswith('magnet:') else '',
                    torrent_files=torrent_files,
                    torrent_name=torrent_name,
                    total_size=total_size,
                    step='confirm'
                )
            except Exception as e:
                flash(f'Error fetching torrent info: {str(e)}', 'danger')
                return render_template(
                    'add_torrent.html',
                    selection_mode=selection_mode,
                    magnet_link=magnet_link,
                    uploaded_file_path=uploaded_file_path
                )

        selected_indices = None
        if selection_mode == 'select':
            selected_indices = [int(i) for i in request.form.getlist('selected_files') if i.isdigit()]
            if not selected_indices:
                flash('Select at least one file to download', 'danger')
                try:
                    torrent_client = TorrentClient()
                    torrent_info = asyncio.run(torrent_client.get_torrent_info(source_path))
                    torrent_files = torrent_info.files
                    torrent_name = torrent_info.name
                    total_size = torrent_info.total_size
                except Exception:
                    torrent_files = []
                return render_template(
                    'add_torrent.html',
                    selection_mode=selection_mode,
                    magnet_link=magnet_link if source_path.startswith('magnet:') else '',
                    uploaded_file_path=uploaded_file_path if not source_path.startswith('magnet:') else '',
                    torrent_files=torrent_files,
                    torrent_name=torrent_name,
                    total_size=total_size,
                    step='confirm'
                )

        try:
            torrent_info = None
            selected_total_size = None

            # Try to fetch full metadata so the name/info-hash are correct immediately
            try:
                torrent_client = TorrentClient()
                torrent_info = asyncio.run(torrent_client.get_torrent_info(source_path))
            except Exception as meta_err:
                app.logger.warning(f"Non-blocking metadata prefetch failed: {meta_err}")

            fallback_name, fallback_hash, fallback_size = extract_submission_metadata(source_path)
            effective_name = (torrent_info.name if torrent_info else fallback_name) or "Processing..."
            effective_hash = (torrent_info.info_hash if torrent_info else fallback_hash) or "pending"

            if selection_mode == 'select' and selected_indices and torrent_info:
                selected_total_size = sum(
                    f.size for f in torrent_info.files if f.index in selected_indices
                )
            elif torrent_info:
                selected_total_size = torrent_info.total_size
            elif fallback_size:
                selected_total_size = fallback_size

            if selected_total_size and not current_user.can_download(selected_total_size):
                remaining = current_user.get_remaining_quota_gb()
                flash(Markup(f"Download exceeds your daily quota. Remaining: {remaining} GB. <a href='{url_for('upgrade')}' class='alert-link'>Upgrade to increase your limit.</a>"), 'danger')
                return render_template(
                    'add_torrent.html',
                    selection_mode=selection_mode,
                    magnet_link=magnet_link,
                    uploaded_file_path=uploaded_file_path,
                    torrent_files=torrent_files,
                    torrent_name=torrent_name,
                    total_size=selected_total_size
                )

            # If this torrent already exists on Drive, reuse it instead of downloading again
            existing_torrent = None
            if effective_hash and effective_hash != "pending":
                existing_torrent = Torrent.query.filter(
                    Torrent.info_hash == effective_hash,
                    Torrent.status == 'completed',
                    Torrent.gdrive_link.isnot(None)
                ).first()

            if not existing_torrent and effective_name:
                existing_torrent = Torrent.query.filter(
                    Torrent.name.ilike(effective_name),
                    Torrent.status == 'completed',
                    Torrent.gdrive_link.isnot(None)
                ).order_by(Torrent.completed_at.desc()).first()

            if existing_torrent:
                total_size_value = selected_total_size or existing_torrent.total_size
                torrent = Torrent(
                    user_id=current_user.id,
                    name=effective_name or existing_torrent.name,
                    info_hash=effective_hash,
                    magnet_link=source_path,
                    total_size=total_size_value,
                    status='completed',
                    progress=100.0,
                    gdrive_link=existing_torrent.gdrive_link,
                    gdrive_path=existing_torrent.gdrive_path,
                    index_link=existing_torrent.index_link,
                    selection_mode=selection_mode,
                    selected_file_indices=','.join(str(i) for i in selected_indices) if selected_indices else None,
                    completed_at=datetime.utcnow()
                )
                db.session.add(torrent)
                db.session.flush()

                if existing_torrent.files:
                    for f in existing_torrent.files:
                        if selected_indices and f.file_index not in selected_indices:
                            continue
                        db.session.add(TorrentFile(
                            torrent_id=torrent.id,
                            file_path=f.file_path,
                            file_size=f.file_size,
                            file_index=f.file_index,
                            is_selected=(selected_indices is None or f.file_index in selected_indices),
                            gdrive_link=f.gdrive_link,
                            index_link=f.index_link
                        ))

                db.session.commit()
                flash('Torrent already available on Google Drive. Linked existing files.', 'info')
                return redirect(url_for('torrent_detail', torrent_id=torrent.id))

            torrent = Torrent(
                user_id=current_user.id,
                name=effective_name,
                info_hash=effective_hash,
                magnet_link=source_path,
                total_size=selected_total_size,
                status='queued',
                selection_mode=selection_mode,
                selected_file_indices=','.join(str(i) for i in selected_indices) if selected_indices else None
            )
            db.session.add(torrent)
            db.session.commit()

            flash('Torrent added to queue!', 'success')
            return redirect(url_for('torrent_detail', torrent_id=torrent.id))

        except Exception as e:
            flash(f'Error adding torrent: {str(e)}', 'danger')

    return render_template(
        'add_torrent.html',
        selection_mode=selection_mode,
        magnet_link=magnet_link,
        uploaded_file_path=uploaded_file_path,
        torrent_files=torrent_files,
        torrent_name=torrent_name,
        total_size=total_size
    )


@app.route('/search-torrents', methods=['GET', 'POST'])
@login_required
def search_torrents_page():
    """Search for torrents."""
    results = []
    query = ''
    page = 1
    show_count = 20  # Initial display count

    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        page = int(request.form.get('page', 1))
        show_all = request.form.get('show_all', 'false') == 'true'

        if query:
            try:
                # Get more results per source for better coverage
                all_results = search_torrents(query, limit_per_source=25, page=page)

                if show_all:
                    # Show all results
                    results = all_results
                else:
                    # Show only first 20 results initially
                    results = all_results[:show_count]

                # Store total count for "see more" button
                total_results = len(all_results)

            except Exception as e:
                flash(f'Error searching torrents: {str(e)}', 'danger')
                total_results = 0
    else:
        # GET request - check for query parameter
        query = request.args.get('query', '').strip()
        page = int(request.args.get('page', 1))
        show_all = request.args.get('show_all', 'false') == 'true'

        if query:
            try:
                all_results = search_torrents(query, limit_per_source=25, page=page)

                if show_all:
                    results = all_results
                else:
                    results = all_results[:show_count]

                total_results = len(all_results)
            except Exception as e:
                flash(f'Error searching torrents: {str(e)}', 'danger')
                total_results = 0
        else:
            total_results = 0

    return render_template('search_torrents.html',
                         results=results,
                         query=query,
                         page=page,
                         total_results=total_results if query else 0,
                         showing_count=len(results))


VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv')


def clean_title(raw_title: str) -> str:
    """Normalize torrent/movie names before querying TMDB."""
    if not raw_title:
        return ''

    # Remove file extension and common separators
    title = Path(raw_title).name
    title = os.path.splitext(title)[0]
    title = title.replace('.', ' ').replace('_', ' ').replace('-', ' ')

    # Remove common release tags
    tags_pattern = r"\b(720p|1080p|2160p|4k|hdr|x264|x265|bluray|web\-dl|webdl|webrip|hdtv|dvdrip|xvid|hevc|10bit|8bit)\b"
    title = re.sub(tags_pattern, '', title, flags=re.IGNORECASE)

    # Remove extra spaces
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def guess_movie_title(torrent):
    """Determine the best title to query TMDB with."""
    if torrent.files:
        for file in torrent.files:
            if file.file_path.lower().endswith(VIDEO_EXTENSIONS):
                cleaned = clean_title(file.file_path)
                if cleaned:
                    return cleaned
    return clean_title(torrent.name)


def get_tmdb_movie_details(title: str):
    """Fetch movie metadata from TMDB.

    Supports both API key (v3) and bearer token (v4) authentication so deployments
    that only set TMDB_TOKEN keep working. The bearer token is automatically
    prefixed if the environment variable omits "Bearer ".
    """

    if not title:
        return None

    api_key = os.environ.get('TMDB_API_KEY') or os.environ.get('TMDB_API')
    bearer = os.environ.get('TMDB_BEARER') or os.environ.get('TMDB_TOKEN')

    if not api_key and not bearer:
        return None

    headers = {'Accept': 'application/json'}
    params = {'query': title, 'include_adult': False}

    if bearer:
        headers['Authorization'] = bearer if bearer.lower().startswith('bearer ') else f'Bearer {bearer}'
    elif api_key:
        params['api_key'] = api_key

    try:
        response = requests.get(
            'https://api.themoviedb.org/3/search/movie',
            headers=headers,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        if not data.get('results'):
            return None

        movie = data['results'][0]
        if not movie:
            return None

        poster_path = movie.get('poster_path')
        return {
            'title': movie.get('title'),
            'overview': movie.get('overview'),
            'rating': movie.get('vote_average'),
            'poster_url': f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None,
            'release_date': movie.get('release_date')
        }
    except Exception:
        return None


@app.route('/torrent/<int:torrent_id>')
@login_required
def torrent_detail(torrent_id):
    """View torrent details."""
    torrent = Torrent.query.get_or_404(torrent_id)

    # Check ownership
    if torrent.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    tmdb_query = guess_movie_title(torrent)
    tmdb_info = get_tmdb_movie_details(tmdb_query) if tmdb_query else None

    return render_template('torrent_detail.html', torrent=torrent, tmdb_info=tmdb_info)


@app.route('/torrent/<int:torrent_id>/delete', methods=['POST'])
@login_required
def delete_torrent(torrent_id):
    """Delete torrent."""
    torrent = Torrent.query.get_or_404(torrent_id)

    # Check ownership
    if torrent.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    db.session.delete(torrent)
    db.session.commit()

    flash('Torrent deleted', 'success')
    return redirect(url_for('dashboard'))


@app.route('/report-problem')
@login_required
def report_problem():
    """Simple contact page for reporting issues."""
    return render_template('report_problem.html')


@app.route('/player/<int:file_id>')
@login_required
def player(file_id):
    """Video player page."""
    torrent_file = TorrentFile.query.get_or_404(file_id)
    torrent = torrent_file.torrent

    # Check ownership
    if torrent.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('player.html', file=torrent_file, torrent=torrent)


# Mega.nz Routes
@app.route('/add-mega', methods=['GET', 'POST'])
@login_required
def add_mega():
    """Add Mega.nz download."""
    if request.method == 'POST':
        mega_link = request.form.get('mega_link')

        if not mega_link or 'mega.nz' not in mega_link.lower():
            flash('Invalid Mega.nz link', 'danger')
            return render_template('add_mega.html')

        try:
            # Initialize Mega downloader
            mega = MegaDownloader()

            # Get file/folder info
            info = mega.get_file_info(mega_link)

            # Check download quota
            if not current_user.can_download(info['size']):
                remaining = current_user.get_remaining_quota_gb()
                flash(Markup(f"Download exceeds your daily quota. Remaining: {remaining} GB. <a href='{url_for('upgrade')}' class='alert-link'>Upgrade to increase your limit.</a>"), 'danger')
                return render_template('add_mega.html')

            # Create torrent entry for Mega download
            torrent = Torrent(
                user_id=current_user.id,
                name=info['name'],
                info_hash=f"mega_{mega_link.split('/')[-1][:10]}",  # Pseudo hash for Mega
                magnet_link=mega_link,
                total_size=info['size'],
                status='queued'
            )
            db.session.add(torrent)
            db.session.commit()

            flash('Mega.nz download added to queue!', 'success')
            return redirect(url_for('torrent_detail', torrent_id=torrent.id))

        except Exception as e:
            flash(f'Error adding Mega.nz download: {str(e)}', 'danger')

    return render_template('add_mega.html')


@app.route('/webhook/genie', methods=['POST'])
def genie_webhook():
    """Webhook for Genie Business Connect payment updates."""
    data = request.get_json(force=True) or {}

    reference = data.get('reference') or (data.get('metadata') or {}).get('reference') or data.get('localId')
    payment_id = data.get('payment_id') or data.get('id') or (data.get('data') or {}).get('id')
    status = (data.get('status') or data.get('state') or (data.get('data') or {}).get('state') or '').lower()
    plan_key = (data.get('metadata') or {}).get('plan_key')

    txn = None
    if reference:
        txn = PaymentTransaction.query.filter_by(reference=reference).first()
    if not txn and payment_id:
        txn = PaymentTransaction.query.filter_by(gateway_payment_id=str(payment_id)).first()

    if not txn:
        return jsonify({'status': 'ignored'}), 200

    if payment_id and not txn.gateway_payment_id:
        txn.gateway_payment_id = str(payment_id)

    _attach_gateway_response(txn, data)

    if status in ('paid', 'success', 'completed', 'succeeded', 'confirmed', 'approved'):
        txn.mark_paid()
        apply_paid_plan(txn.user, plan_key or txn.plan_key)
        return jsonify({'status': 'upgraded'}), 200

    if status in ('failed', 'canceled', 'cancelled', 'declined', 'rejected', 'voided'):
        txn.mark_failed(f"status={status}")
        return jsonify({'status': 'failed'}), 200

    db.session.commit()
    return jsonify({'status': status or 'pending'}), 200


# Admin Routes
@app.route('/admin')
@login_required
def admin_panel():
    """Admin panel."""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    users = User.query.order_by(User.created_at.desc()).all()
    invite_codes = InviteCode.query.order_by(InviteCode.created_at.desc()).all()
    total_torrents = Torrent.query.count()

    return render_template('admin.html', users=users, invite_codes=invite_codes, total_torrents=total_torrents)


@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    """Delete user (admin only)."""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)

    if user.is_admin:
        flash('Cannot delete admin user', 'danger')
        return redirect(url_for('admin_panel'))

    db.session.delete(user)
    db.session.commit()

    flash(f'User {user.username} deleted', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/user/<int:user_id>/reset-password', methods=['POST'])
@login_required
def admin_reset_password(user_id):
    """Reset user password (admin only)."""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')

    if not new_password:
        flash('Password is required', 'danger')
        return redirect(url_for('admin_panel'))

    user.set_password(new_password)
    db.session.commit()

    flash(f'Password reset for {user.username}', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/user/<int:user_id>/set-limit', methods=['POST'])
@login_required
def admin_set_user_limit(user_id):
    """Set user download limit (admin only)."""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    daily_limit_gb = request.form.get('daily_limit_gb', '').strip()

    # Convert GB to bytes
    if not daily_limit_gb or daily_limit_gb == '0':
        user.daily_limit = 0  # Unlimited
        user.base_daily_limit = 0
        flash(f'Download limit removed for {user.username} (Unlimited)', 'success')
    else:
        try:
            daily_limit_bytes = int(float(daily_limit_gb) * (1024 ** 3))
            user.daily_limit = daily_limit_bytes
            user.base_daily_limit = daily_limit_bytes
            flash(f'Daily limit set to {daily_limit_gb} GB for {user.username}', 'success')
        except ValueError:
            flash('Invalid limit value', 'danger')
            return redirect(url_for('admin_panel'))

    db.session.commit()
    return redirect(url_for('admin_panel'))


@app.route('/admin/invite-code/create', methods=['POST'])
@login_required
def admin_create_invite():
    """Create invite code (admin only)."""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    code = request.form.get('code')
    max_uses = int(request.form.get('max_uses', 1))
    daily_limit_gb = request.form.get('daily_limit_gb', '').strip()

    if not code:
        flash('Code is required', 'danger')
        return redirect(url_for('admin_panel'))

    # Check if code exists
    if InviteCode.query.filter_by(code=code).first():
        flash('Code already exists', 'danger')
        return redirect(url_for('admin_panel'))

    # Convert GB to bytes for daily limit
    daily_limit_bytes = 0
    if daily_limit_gb:
        try:
            daily_limit_bytes = int(float(daily_limit_gb) * (1024 ** 3))
        except ValueError:
            flash('Invalid daily limit value', 'danger')
            return redirect(url_for('admin_panel'))

    invite = InviteCode(
        code=code,
        max_uses=max_uses,
        daily_download_limit=daily_limit_bytes,
        created_by=current_user.id
    )
    db.session.add(invite)
    db.session.commit()

    flash(f'Invite code created: {code}', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/invite-code/<int:invite_id>/toggle', methods=['POST'])
@login_required
def admin_toggle_invite(invite_id):
    """Toggle invite code active status (admin only)."""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    invite = InviteCode.query.get_or_404(invite_id)
    invite.is_active = not invite.is_active
    db.session.commit()

    status = 'activated' if invite.is_active else 'deactivated'
    flash(f'Invite code {status}', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/invite-code/<int:invite_id>/update', methods=['POST'])
@login_required
def admin_update_invite(invite_id):
    """Update invite code limits and activation (admin only)."""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    invite = InviteCode.query.get_or_404(invite_id)
    max_uses = request.form.get('max_uses', '').strip()
    daily_limit_gb = request.form.get('daily_limit_gb', '').strip()
    is_active = request.form.get('is_active') == 'on'

    try:
        if max_uses:
            invite.max_uses = int(max_uses)
        invite.is_active = is_active

        if daily_limit_gb == '' or daily_limit_gb == '0':
            invite.daily_download_limit = 0
        else:
            invite.daily_download_limit = int(float(daily_limit_gb) * (1024 ** 3))

        db.session.commit()
        flash('Invite code updated', 'success')
    except ValueError:
        flash('Invalid values for invite code update', 'danger')

    return redirect(url_for('admin_panel'))


@app.route('/admin/empty-drive', methods=['POST'])
@login_required
def admin_empty_drive():
    """Empty Google Drive folder (admin only - DANGER ZONE)."""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    # Require confirmation via POST parameter
    confirmation = request.form.get('confirmation', '').strip()
    if confirmation != 'DELETE ALL FILES':
        flash('Invalid confirmation. Please type "DELETE ALL FILES" to confirm.', 'danger')
        return redirect(url_for('admin_panel'))

    try:
        # Import here to avoid circular imports
        from drive import RcloneManager
        import asyncio

        rclone = RcloneManager()

        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(rclone.empty_drive_folder())
        loop.close()

        if result['success']:
            # Also delete all torrent records from database
            deleted_count = Torrent.query.delete()
            db.session.commit()

            flash(f'✓ Drive folder emptied successfully! Deleted {deleted_count} torrent records.', 'success')
            logger.info(f"Admin {current_user.username} emptied drive folder and deleted {deleted_count} torrent records")
        else:
            flash(f'Failed to empty drive: {result["message"]}', 'danger')

    except Exception as e:
        logger.error(f"Error emptying drive folder: {e}", exc_info=True)
        flash(f'Error: {str(e)}', 'danger')

    return redirect(url_for('admin_panel'))


# API Routes
@app.route('/api/torrent/<int:torrent_id>/status')
@login_required
def api_torrent_status(torrent_id):
    """Get torrent status (API)."""
    torrent = Torrent.query.get_or_404(torrent_id)

    # Check ownership
    if torrent.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({
        'id': torrent.id,
        'name': torrent.name,
        'status': torrent.status,
        'progress': torrent.progress,
        'gdrive_link': torrent.gdrive_link,
        'index_link': torrent.index_link,
        'error_message': torrent.error_message
    })


@app.route('/terms')
def terms():
    """Terms and Conditions page."""
    return render_template('terms.html')


@app.route('/privacy-policy')
def privacy_policy():
    """Privacy Policy page."""
    return render_template('privacy_policy.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
