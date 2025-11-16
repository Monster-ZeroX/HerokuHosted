"""
Database models for the web application.
"""
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

    # Relationships
    torrents = db.relationship('Torrent', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if password matches."""
        return check_password_hash(self.password_hash, password)

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

    def is_valid(self):
        """Check if invite code is valid."""
        return self.is_active and (self.max_uses == -1 or self.times_used < self.max_uses)

    def use(self):
        """Mark invite code as used."""
        self.times_used += 1
        if self.max_uses != -1 and self.times_used >= self.max_uses:
            self.is_active = False

    def __repr__(self):
        return f'<InviteCode {self.code}>'


def init_db(app):
    """Initialize database with default data."""
    db.init_app(app)

    with app.app_context():
        db.create_all()

        # Create admin user if doesn't exist
        admin = User.query.filter_by(username='MonsterZeroX').first()
        if not admin:
            admin = User(username='MonsterZeroX', is_admin=True)
            admin.set_password('Kaveesha@2005')
            db.session.add(admin)

        # Create default invite code if doesn't exist
        invite = InviteCode.query.filter_by(code='Kaveesha').first()
        if not invite:
            invite = InviteCode(code='Kaveesha', max_uses=-1)  # Unlimited uses
            db.session.add(invite)

        db.session.commit()
        print("Database initialized successfully")
