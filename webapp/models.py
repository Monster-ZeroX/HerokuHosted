"""
Database models for the web application.
"""
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
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

        if self.is_admin or not self.daily_limit:
            return None  # Unlimited

        remaining = self.daily_limit - (self.daily_downloaded or 0)
        return max(0, round(remaining / (1024 ** 3), 2))

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)

    # File information
    files = db.relationship('TorrentFile', backref='torrent', lazy=True, cascade='all, delete-orphan')

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


def init_db(app):
    """Initialize database with default data."""
    db.init_app(app)

    with app.app_context():
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
