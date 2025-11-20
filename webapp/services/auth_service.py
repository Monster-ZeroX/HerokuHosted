"""Authentication and OTP flows."""
from __future__ import annotations

import os
import random
from datetime import datetime, timedelta
from typing import Optional

import requests
from flask import session

from webapp.models import db, User, EmailOTP

MAILEROO_URL = "https://smtp.maileroo.com/send"


def _generate_code() -> str:
    return f"{random.randint(100000, 999999)}"


class AuthService:
    def __init__(self):
        pass

    def _send_email(self, email: str, subject: str, body: str) -> None:
        api_key = os.environ.get("MAILEROO_API_KEY")
        sender = os.environ.get("MAILEROO_SENDER", "noreply@directtorrent.me")
        if not api_key:
            # In test/dev environments, just log.
            print(f"[MAILEROO] {subject} -> {email}: {body}")
            return
        payload = {
            "from": sender,
            "to": email,
            "subject": subject,
            "text": body,
        }
        try:
            requests.post(
                MAILEROO_URL,
                auth=("api", api_key),
                data=payload,
                timeout=10,
            )
        except Exception:
            # Do not block user creation if email fails in dev
            print(f"Failed to send email to {email}")

    def register_start(self, username: str, email: str, password: str) -> dict:
        code = _generate_code()
        otp = EmailOTP(
            email=email.lower().strip(),
            code=code,
            purpose="registration",
            expires_at=datetime.utcnow() + timedelta(minutes=10),
            payload={"username": username, "password": password},
        )
        db.session.add(otp)
        db.session.commit()
        self._send_email(email, "Your DirectTorrent.me verification code", f"Your code is {code}")
        return {"ok": True, "message": "OTP sent to email"}

    def _create_user_from_payload(self, payload: dict, email: str) -> User:
        user = User(
            username=payload["username"],
            email=email.lower().strip(),
            plan_type="free",
            daily_limit_gb=5.0,
            base_daily_limit_gb=5.0,
        )
        user.set_password(payload["password"])
        db.session.add(user)
        db.session.commit()
        return user

    def register_verify(self, email: str, code: str) -> dict:
        otp = (
            EmailOTP.query.filter_by(email=email.lower().strip(), purpose="registration")
            .order_by(EmailOTP.created_at.desc())
            .first()
        )
        if not otp or not otp.is_valid(code):
            return {"ok": False, "error": "INVALID_OTP"}
        otp.consumed_at = datetime.utcnow()
        user = User.query.filter_by(email=email.lower().strip()).first()
        if not user:
            user = self._create_user_from_payload(otp.payload or {}, email)
        db.session.commit()
        session["user_id"] = user.id
        session.permanent = True
        return {"ok": True, "user": self._serialize_user(user)}

    def login(self, email_or_username: str, password: str) -> dict:
        user = User.query.filter(
            (User.email == email_or_username.lower()) | (User.username == email_or_username)
        ).first()
        if not user or not user.check_password(password):
            return {"ok": False, "error": "INVALID_CREDENTIALS"}
        session["user_id"] = user.id
        session.permanent = True
        user.last_login = datetime.utcnow()
        db.session.commit()
        return {"ok": True, "user": self._serialize_user(user)}

    def logout(self) -> dict:
        session.clear()
        return {"ok": True}

    def me(self) -> dict:
        user = self._current_user()
        if not user:
            return {"authenticated": False}
        return {"authenticated": True, "user": self._serialize_user(user)}

    def password_reset_start(self, email: str) -> dict:
        code = _generate_code()
        otp = EmailOTP(
            email=email.lower().strip(),
            code=code,
            purpose="password_reset",
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        db.session.add(otp)
        db.session.commit()
        self._send_email(email, "Password reset code", f"Your reset code is {code}")
        return {"ok": True}

    def password_reset_complete(self, email: str, code: str, new_password: str) -> dict:
        otp = (
            EmailOTP.query.filter_by(email=email.lower().strip(), purpose="password_reset")
            .order_by(EmailOTP.created_at.desc())
            .first()
        )
        if not otp or not otp.is_valid(code):
            return {"ok": False, "error": "INVALID_OTP"}
        user = User.query.filter_by(email=email.lower().strip()).first()
        if not user:
            return {"ok": False, "error": "INVALID_OTP"}
        otp.consumed_at = datetime.utcnow()
        user.set_password(new_password)
        db.session.commit()
        return {"ok": True}

    def _current_user(self) -> Optional[User]:
        user_id = session.get("user_id")
        if not user_id:
            return None
        return User.query.get(user_id)

    def _serialize_user(self, user: User) -> dict:
        user.ensure_plan_valid()
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": bool(user.is_admin),
            "plan": user.plan,
        }
