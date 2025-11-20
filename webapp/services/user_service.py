"""User-related business logic."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import or_

from webapp.models import db, User


class UserService:
    def __init__(self):
        pass

    def get_user(self, user_id: int) -> Optional[User]:
        return User.query.get(user_id)

    def list_users(self, plan_type: str | None, search: str | None, page: int, page_size: int):
        query = User.query
        if plan_type:
            query = query.filter(User.plan_type == plan_type)
        if search:
            query = query.filter(or_(User.email.ilike(f"%{search}%"), User.username.ilike(f"%{search}%")))
        total = query.count()
        items = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update_user(self, user: User, data: dict) -> User:
        if "plan_type" in data:
            user.plan_type = data["plan_type"]
        if "plan_expires_at" in data:
            user.plan_expires_at = data["plan_expires_at"]
        if "is_active" in data:
            user.is_active = data["is_active"]
        if "daily_limit_gb" in data:
            user.daily_limit_gb = data["daily_limit_gb"]
        db.session.commit()
        return user

    def reset_usage(self, user: User) -> User:
        user.usage_today_bytes = 0
        db.session.commit()
        return user

    def serialize_admin(self, user: User) -> dict:
        user.ensure_plan_valid()
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "plan_type": user.plan_type,
            "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "is_active": bool(user.is_active),
            "usage_today_gb": round((user.usage_today_bytes or 0) / (1024 ** 3), 2),
        }

    def serialize_full(self, user: User) -> dict:
        data = self.serialize_admin(user)
        data.update(
            {
                "total_bandwidth_gb": round((user.total_usage_bytes or 0) / (1024 ** 3), 2),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "plan": user.plan,
            }
        )
        return data
