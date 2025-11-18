"""Database models for DirectTorrent.me backend."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, date
from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Global extension instance

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    plan_type = db.Column(db.String(20), default="free")
    plan_expires_at = db.Column(db.DateTime)
    daily_limit_gb = db.Column(db.Float, default=5.0)
    base_daily_limit_gb = db.Column(db.Float, default=5.0)

    usage_today_bytes = db.Column(db.BigInteger, default=0)
    usage_last_reset = db.Column(db.Date, default=lambda: datetime.utcnow().date())
    total_usage_bytes = db.Column(db.BigInteger, default=0)

    jobs = db.relationship("TransferJob", backref="user", lazy=True, cascade="all, delete-orphan")
    transactions = db.relationship("Transaction", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def reset_usage_if_needed(self) -> None:
        today = datetime.utcnow().date()
        if self.usage_last_reset != today:
            self.usage_today_bytes = 0
            self.usage_last_reset = today
            db.session.flush()

    def add_usage(self, amount_bytes: int) -> None:
        self.reset_usage_if_needed()
        self.usage_today_bytes = (self.usage_today_bytes or 0) + amount_bytes
        self.total_usage_bytes = (self.total_usage_bytes or 0) + amount_bytes

    @property
    def plan(self) -> dict:
        self.reset_usage_if_needed()
        plan_type = self.plan_type or "free"
        limit_gb = self.daily_limit_gb or 0
        usage_today_gb = round((self.usage_today_bytes or 0) / (1024 ** 3), 2)
        features: list[str] = []
        if plan_type == "paid":
            features = ["priority_speed", "priority_support"]
        return {
            "type": plan_type,
            "name": "Pro" if plan_type == "paid" else "Free",
            "expires_at": self.plan_expires_at.isoformat() if self.plan_expires_at else None,
            "usage_today_gb": usage_today_gb,
            "limit_today_gb": limit_gb,
            "features": features,
        }

    def ensure_plan_valid(self) -> None:
        if self.plan_type == "paid" and self.plan_expires_at and datetime.utcnow() > self.plan_expires_at:
            self.plan_type = "free"
            self.plan_expires_at = None
            self.daily_limit_gb = self.base_daily_limit_gb or 5.0

    def has_capacity(self, size_bytes: int) -> bool:
        self.ensure_plan_valid()
        self.reset_usage_if_needed()
        if self.is_admin:
            return True
        if not self.daily_limit_gb:
            return True
        limit_bytes = float(self.daily_limit_gb) * (1024 ** 3)
        return (self.usage_today_bytes or 0) + size_bytes <= limit_bytes

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email}>"


class EmailOTP(db.Model):
    __tablename__ = "email_otps"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(10), nullable=False)
    purpose = db.Column(db.String(50), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    consumed_at = db.Column(db.DateTime)
    payload = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_valid(self, code: str) -> bool:
        return (
            self.code == code
            and not self.consumed_at
            and datetime.utcnow() <= self.expires_at
        )


class TransferJob(db.Model):
    __tablename__ = "transfer_jobs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(255))
    source_type = db.Column(db.String(20), nullable=False)  # torrent | mega
    magnet_link = db.Column(db.Text)
    source_url = db.Column(db.Text)
    status = db.Column(db.String(20), default="queued")
    progress = db.Column(db.Float, default=0.0)
    size_bytes = db.Column(db.BigInteger)
    bytes_downloaded = db.Column(db.BigInteger, default=0)
    download_speed = db.Column(db.Float, default=0.0)
    upload_speed = db.Column(db.Float, default=0.0)
    eta_seconds = db.Column(db.Integer)
    drive_folder_url = db.Column(db.String(500))
    stream_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    app_role = db.Column(db.String(10), default="FREE")
    app_instance = db.Column(db.String(100))

    error_message = db.Column(db.Text)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "source_type": self.source_type,
            "magnet_link": self.magnet_link,
            "source_url": self.source_url,
            "status": self.status,
            "progress": self.progress,
            "size_bytes": self.size_bytes,
            "bytes_downloaded": self.bytes_downloaded,
            "download_speed": self.download_speed,
            "upload_speed": self.upload_speed,
            "eta_seconds": self.eta_seconds,
            "drive_folder_url": self.drive_folder_url,
            "stream_url": self.stream_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "app_role": self.app_role,
            "app_instance": self.app_instance,
        }


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="USD")
    status = db.Column(db.String(20), default="pending")
    provider = db.Column(db.String(50), default="genie")
    provider_transaction_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


__all__ = [
    "db",
    "User",
    "EmailOTP",
    "TransferJob",
    "Transaction",
]
