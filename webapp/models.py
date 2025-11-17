"""
Database models for the web application.
"""
import os
from datetime import datetime, timedelta
from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Download usage tracking (in bytes)
    total_downloaded = db.Column(db.BigInteger, default=0)
    daily_downloaded = db.Column(db.BigInteger, default=0)
    last_reset_date = db.Column(db.Date, default=datetime.utcnow().date)

    # Daily download limit (in bytes, 0 = unlimited)
    daily_limit = db.Column(db.BigInteger, default=0)

    # Subscription details
    base_daily_limit = db.Column(db.BigInteger, default=0)
    subscription_plan = db.Column(db.String(50))
    subscription_expires_at = db.Column(db.DateTime)

    # Relationships
    torrents = db.relationship('Torrent', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if password matches."""
        return check_password_hash(self.password_hash, password)

    def reset_daily_usage_if_needed(self):
        """Reset daily usage if it's a new day."""
        today = datetime.utcnow().date()
        if self.last_reset_date != today:
            self.daily_downloaded = 0
            self.last_reset_date = today
            db.session.commit()
        self.ensure_subscription_is_current()

    def add_download_usage(self, bytes_downloaded):
        """Add to download usage tracking."""
        self.reset_daily_usage_if_needed()
        self.total_downloaded = (self.total_downloaded or 0) + bytes_downloaded
        self.daily_downloaded = (self.daily_downloaded or 0) + bytes_downloaded
        db.session.commit()

    def get_daily_usage_gb(self):
        """Get daily usage in GB."""
        self.reset_daily_usage_if_needed()
        return round((self.daily_downloaded or 0) / (1024 ** 3), 2)

    def get_total_usage_gb(self):
        """Get total usage in GB."""
        return round((self.total_downloaded or 0) / (1024 ** 3), 2)

    def get_daily_limit_gb(self):
        """Get daily limit in GB."""
        if not self.daily_limit:
            return None  # Unlimited
        return round(self.daily_limit / (1024 ** 3), 2)

    def can_download(self, size_bytes):
        """Check if user can download given size."""
        self.reset_daily_usage_if_needed()

        # Admins have unlimited access
        if self.is_admin:
            return True

        # If no limit set, allow
        if not self.daily_limit:
            return True

        # Check if adding this download would exceed limit
        new_total = (self.daily_downloaded or 0) + size_bytes
        return new_total <= self.daily_limit

    def get_remaining_quota_gb(self):
        """Get remaining daily quota in GB."""
        self.reset_daily_usage_if_needed()

        # Downgrade expired subscriptions before calculating
        self.ensure_subscription_is_current()

        if self.is_admin or not self.daily_limit:
            return None  # Unlimited

        remaining = self.daily_limit - (self.daily_downloaded or 0)
        return max(0, round(remaining / (1024 ** 3), 2))

    def ensure_subscription_is_current(self):
        """Revert to base limits when a paid plan expires."""
        if self.subscription_expires_at and datetime.utcnow() > self.subscription_expires_at:
            self.subscription_plan = None
            self.subscription_expires_at = None
            if self.base_daily_limit is not None:
                self.daily_limit = self.base_daily_limit or 0
            db.session.commit()

    def apply_subscription(self, plan_key: str, new_limit_bytes: int, duration_days: int = 30):
        """Set a paid tier for the user."""
        self.subscription_plan = plan_key
        self.subscription_expires_at = datetime.utcnow() + timedelta(days=duration_days)
        self.daily_limit = new_limit_bytes
        db.session.commit()

    @property
    def is_paid(self) -> bool:
        """Return True when the user currently has an active paid subscription."""
        self.ensure_subscription_is_current()

        if not self.subscription_plan:
            return False

        if self.subscription_expires_at and datetime.utcnow() > self.subscription_expires_at:
            return False

        return True

    def __repr__(self):
        return f'<User {self.username}>'


class Torrent(db.Model):
    """Torrent model for tracking downloads."""
    __tablename__ = 'torrents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    info_hash = db.Column(db.String(40), nullable=False)
    magnet_link = db.Column(db.Text)
    total_size = db.Column(db.BigInteger)
    status = db.Column(db.String(20), default='queued')  # queued, downloading, uploading, completed, failed
    progress = db.Column(db.Float, default=0.0)
    gdrive_path = db.Column(db.String(500))
    gdrive_link = db.Column(db.String(500))
    index_link = db.Column(db.String(500))
    download_rate = db.Column(db.Float, default=0.0)
    eta_seconds = db.Column(db.Integer)
    selection_mode = db.Column(db.String(20), default='all')  # all, select
    selected_file_indices = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)

    # File information
    files = db.relationship('TorrentFile', backref='torrent', lazy=True, cascade='all, delete-orphan')

    def selected_indices(self):
        """Return parsed list of selected file indices (or None for all)."""
        if self.selection_mode != 'select' or not self.selected_file_indices:
            return None

        indices = []
        for part in self.selected_file_indices.split(','):
            part = part.strip()
            if part.isdigit():
                indices.append(int(part))
        return indices or None

    def __repr__(self):
        return f'<Torrent {self.name}>'


class TorrentFile(db.Model):
    """Individual files in a torrent."""
    __tablename__ = 'torrent_files'

    id = db.Column(db.Integer, primary_key=True)
    torrent_id = db.Column(db.Integer, db.ForeignKey('torrents.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.BigInteger)
    file_index = db.Column(db.Integer)
    is_selected = db.Column(db.Boolean, default=True)
    gdrive_link = db.Column(db.String(500))
    index_link = db.Column(db.String(500))

    def __repr__(self):
        return f'<TorrentFile {self.file_path}>'


class InviteCode(db.Model):
    """Invite codes for registration."""
    __tablename__ = 'invite_codes'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    max_uses = db.Column(db.Integer, default=1)
    times_used = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Download limit for users created with this code (in bytes, 0 = unlimited)
    daily_download_limit = db.Column(db.BigInteger, default=0)

    def is_valid(self):
        """Check if invite code is valid."""
        return self.is_active and (self.max_uses == -1 or self.times_used < self.max_uses)

    def use(self):
        """Mark invite code as used."""
        self.times_used += 1
        if self.max_uses != -1 and self.times_used >= self.max_uses:
            self.is_active = False

    def get_limit_gb(self):
        """Get download limit in GB."""
        if not self.daily_download_limit:
            return None  # Unlimited
        return round(self.daily_download_limit / (1024 ** 3), 2)

    def __repr__(self):
        return f'<InviteCode {self.code}>'


class PaymentTransaction(db.Model):
    """Tracks upgrade payments initiated through Genie Business Connect."""

    __tablename__ = 'payment_transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_key = db.Column(db.String(50), nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), default='USD')
    status = db.Column(db.String(20), default='pending')  # pending, paid, failed
    reference = db.Column(db.String(100), unique=True, nullable=False)
    gateway_payment_id = db.Column(db.String(100))
    raw_response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('payments', lazy=True))

    def mark_paid(self):
        self.status = 'paid'
        db.session.commit()

    def mark_failed(self, reason: Optional[str] = None):
        self.status = 'failed'
        if reason:
            self.raw_response = reason
        db.session.commit()

    def __repr__(self):
        return f'<PaymentTransaction {self.reference} ({self.status})>'


def init_db(app):
    """Initialize database with default data and apply safe migrations."""
    db.init_app(app)

    def apply_safe_migrations():
        """Ensure critical columns exist to keep the app running after deploys."""
        migrations = [
            ("users.total_downloaded", "ALTER TABLE users ADD COLUMN IF NOT EXISTS total_downloaded BIGINT DEFAULT 0"),
            ("users.daily_downloaded", "ALTER TABLE users ADD COLUMN IF NOT EXISTS daily_downloaded BIGINT DEFAULT 0"),
            ("users.last_reset_date", "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_reset_date DATE DEFAULT CURRENT_DATE"),
            ("users.daily_limit", "ALTER TABLE users ADD COLUMN IF NOT EXISTS daily_limit BIGINT DEFAULT 0"),
            ("invite_codes.daily_download_limit", "ALTER TABLE invite_codes ADD COLUMN IF NOT EXISTS daily_download_limit BIGINT DEFAULT 0"),
            ("torrents.download_rate", "ALTER TABLE torrents ADD COLUMN IF NOT EXISTS download_rate FLOAT DEFAULT 0"),
            ("torrents.eta_seconds", "ALTER TABLE torrents ADD COLUMN IF NOT EXISTS eta_seconds INTEGER"),
            ("torrents.selection_mode", "ALTER TABLE torrents ADD COLUMN IF NOT EXISTS selection_mode VARCHAR(20) DEFAULT 'all'"),
            ("torrents.selected_file_indices", "ALTER TABLE torrents ADD COLUMN IF NOT EXISTS selected_file_indices TEXT"),
            ("users.base_daily_limit", "ALTER TABLE users ADD COLUMN IF NOT EXISTS base_daily_limit BIGINT DEFAULT 0"),
            ("users.subscription_plan", "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_plan VARCHAR(50)"),
            ("users.subscription_expires_at", "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMP"),
        ]

        with db.engine.begin() as conn:
            for label, statement in migrations:
                try:
                    conn.execute(text(statement))
                    print(f"  ✓ ensured {label}")
                except Exception as exc:
                    print(f"  - skipped {label}: {exc}")

            # Seed base_daily_limit for existing users if missing
            try:
                conn.execute(text("UPDATE users SET base_daily_limit = COALESCE(base_daily_limit, daily_limit, 0) WHERE base_daily_limit IS NULL"))
                print("  ✓ synced base_daily_limit defaults")
            except Exception as exc:
                print(f"  - skipped base_daily_limit sync: {exc}")

    with app.app_context():
        apply_safe_migrations()
        db.create_all()

        # Admin credentials can be configured via environment variables
        admin_username = os.environ.get('ADMIN_USERNAME', 'MonsterZeroX')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'Kaveesha@2005')
        default_invite_code = os.environ.get('DEFAULT_INVITE_CODE', 'Kaveesha')

        try:
            # Create admin user if doesn't exist
            admin = User.query.filter_by(username=admin_username).first()
            if not admin:
                admin = User(username=admin_username, is_admin=True)
                admin.set_password(admin_password)
                db.session.add(admin)

            # Create default invite code if doesn't exist
            invite = InviteCode.query.filter_by(code=default_invite_code).first()
            if not invite:
                invite = InviteCode(code=default_invite_code, max_uses=-1)  # Unlimited uses
                db.session.add(invite)

            db.session.commit()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Warning during database initialization: {e}")
            print("Please run migrate_db.py to add new columns to existing database")
            print("Command: python migrate_db.py")
