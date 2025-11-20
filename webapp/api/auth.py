from __future__ import annotations

from flask import Blueprint, request, jsonify

from webapp.services.auth_service import AuthService
from webapp.models import User

auth_bp = Blueprint("auth", __name__)
service = AuthService()


def _require_json():
    if not request.is_json:
        return jsonify({"ok": False, "error": "INVALID_JSON"}), 400


@auth_bp.route("/register/start", methods=["POST"])
def register_start():
    if (resp := _require_json()):
        return resp
    data = request.get_json() or {}
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    if not all([username, email, password]):
        return jsonify({"ok": False, "error": "INVALID_PAYLOAD"}), 400
    if User.query.filter((User.email == email.lower()) | (User.username == username)).first():
        return jsonify({"ok": False, "error": "USER_EXISTS"}), 400
    return jsonify(service.register_start(username, email, password))


@auth_bp.route("/register/verify", methods=["POST"])
def register_verify():
    if (resp := _require_json()):
        return resp
    data = request.get_json() or {}
    email = data.get("email")
    code = data.get("code")
    if not all([email, code]):
        return jsonify({"ok": False, "error": "INVALID_PAYLOAD"}), 400
    result = service.register_verify(email, code)
    status = 200 if result.get("ok") else 400
    return jsonify(result), status


@auth_bp.route("/login", methods=["POST"])
def login():
    if (resp := _require_json()):
        return resp
    data = request.get_json() or {}
    identifier = data.get("email_or_username")
    password = data.get("password")
    if not all([identifier, password]):
        return jsonify({"ok": False, "error": "INVALID_PAYLOAD"}), 400
    result = service.login(identifier, password)
    status = 200 if result.get("ok") else 401
    return jsonify(result), status


@auth_bp.route("/logout", methods=["POST"])
def logout():
    return jsonify(service.logout())


@auth_bp.route("/me", methods=["GET"])
def me():
    return jsonify(service.me())


@auth_bp.route("/password-reset/start", methods=["POST"])
def password_reset_start():
    if (resp := _require_json()):
        return resp
    data = request.get_json() or {}
    email = data.get("email")
    if not email:
        return jsonify({"ok": False, "error": "INVALID_PAYLOAD"}), 400
    return jsonify(service.password_reset_start(email))


@auth_bp.route("/password-reset/complete", methods=["POST"])
def password_reset_complete():
    if (resp := _require_json()):
        return resp
    data = request.get_json() or {}
    email = data.get("email")
    code = data.get("code")
    new_password = data.get("new_password")
    if not all([email, code, new_password]):
        return jsonify({"ok": False, "error": "INVALID_PAYLOAD"}), 400
    result = service.password_reset_complete(email, code, new_password)
    status = 200 if result.get("ok") else 400
    return jsonify(result), status
