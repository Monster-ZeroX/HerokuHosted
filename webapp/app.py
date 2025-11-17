"""
Flask web application for Torrent to Google Drive.
"""
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime

from webapp.models import db, User, Torrent, TorrentFile, InviteCode, init_db
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

# Initialize database
init_db(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


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


@app.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    return redirect(url_for('index'))


# Dashboard Routes
@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    # Reset daily usage if needed
    current_user.reset_daily_usage_if_needed()

    torrents = Torrent.query.filter_by(user_id=current_user.id).order_by(Torrent.created_at.desc()).all()

    # Calculate usage stats
    usage_stats = {
        'daily_usage_gb': current_user.get_daily_usage_gb(),
        'total_usage_gb': current_user.get_total_usage_gb(),
        'daily_limit_gb': current_user.get_daily_limit_gb(),
        'remaining_quota_gb': current_user.get_remaining_quota_gb(),
        'has_limit': current_user.daily_limit > 0 if current_user.daily_limit else False
    }

    return render_template('dashboard.html', torrents=torrents, usage_stats=usage_stats)


@app.route('/add-torrent', methods=['GET', 'POST'])
@login_required
def add_torrent():
    """Add new torrent."""
    if request.method == 'POST':
        magnet_link = request.form.get('magnet_link')

        if not magnet_link or not magnet_link.startswith('magnet:'):
            flash('Invalid magnet link', 'danger')
            return render_template('add_torrent.html')

        try:
            # Get torrent info
            torrent_client = TorrentClient()
            torrent_info = None

            # This would be async in production - simplified for now
            # torrent_info = await torrent_client.get_torrent_info(magnet_link)

            # Create torrent entry
            torrent = Torrent(
                user_id=current_user.id,
                name="Processing...",  # Will be updated when metadata is fetched
                info_hash="pending",
                magnet_link=magnet_link,
                status='queued'
            )
            db.session.add(torrent)
            db.session.commit()

            flash('Torrent added to queue!', 'success')
            return redirect(url_for('torrent_detail', torrent_id=torrent.id))

        except Exception as e:
            flash(f'Error adding torrent: {str(e)}', 'danger')

    return render_template('add_torrent.html')


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


@app.route('/torrent/<int:torrent_id>')
@login_required
def torrent_detail(torrent_id):
    """View torrent details."""
    torrent = Torrent.query.get_or_404(torrent_id)

    # Check ownership
    if torrent.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('torrent_detail.html', torrent=torrent)


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
                flash(f'Download exceeds your daily quota. Remaining: {remaining} GB', 'danger')
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
        flash(f'Download limit removed for {user.username} (Unlimited)', 'success')
    else:
        try:
            daily_limit_bytes = int(float(daily_limit_gb) * (1024 ** 3))
            user.daily_limit = daily_limit_bytes
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
