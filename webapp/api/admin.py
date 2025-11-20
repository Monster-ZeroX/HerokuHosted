from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request, session

from webapp.models import User, TransferJob
from webapp.services.user_service import UserService
from webapp.services.stats_service import StatsService
from webapp.services.billing_service import BillingService

admin_bp = Blueprint("admin", __name__)
users = UserService()
stats = StatsService()
billing = BillingService()


def _current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def _require_admin():
    user = _current_user()
    if not user or not user.is_admin:
        return None, (jsonify({"ok": False, "error": "FORBIDDEN"}), 403)
    return user, None


def _pagination():
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    return page, page_size


@admin_bp.route("/overview", methods=["GET"])
def overview():
    _, error = _require_admin()
    if error:
        return error
    return jsonify(stats.overview())


@admin_bp.route("/users", methods=["GET"])
def list_users():
    _, error = _require_admin()
    if error:
        return error
    plan_type = request.args.get("plan_type")
    search = request.args.get("search")
    page, page_size = _pagination()
    items, total = users.list_users(plan_type, search, page, page_size)
    return jsonify(
        {
            "items": [users.serialize_admin(u) for u in items],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }
    )


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
def user_detail(user_id: int):
    _, error = _require_admin()
    if error:
        return error
    user = users.get_user(user_id)
    if not user:
        return jsonify({"ok": False, "error": "NOT_FOUND"}), 404
    return jsonify({"user": users.serialize_full(user)})


@admin_bp.route("/users/<int:user_id>", methods=["PATCH"])
def update_user(user_id: int):
    _, error = _require_admin()
    if error:
        return error
    user = users.get_user(user_id)
    if not user:
        return jsonify({"ok": False, "error": "NOT_FOUND"}), 404
    data = request.get_json() or {}
    if "plan_expires_at" in data and data["plan_expires_at"]:
        data["plan_expires_at"] = datetime.fromisoformat(data["plan_expires_at"])
    updated = users.update_user(user, data)
    return jsonify({"ok": True, "user": users.serialize_full(updated)})


@admin_bp.route("/users/<int:user_id>/reset-usage", methods=["POST"])
def reset_usage(user_id: int):
    _, error = _require_admin()
    if error:
        return error
    user = users.get_user(user_id)
    if not user:
        return jsonify({"ok": False, "error": "NOT_FOUND"}), 404
    updated = users.reset_usage(user)
    return jsonify({"ok": True, "user": {"id": updated.id, "usage_today_gb": 0}})


@admin_bp.route("/transactions", methods=["GET"])
def list_transactions():
    _, error = _require_admin()
    if error:
        return error
    page, page_size = _pagination()
    items, total = billing.list_transactions(page, page_size)
    return jsonify(
        {
            "items": [
                {
                    "id": txn.id,
                    "user_id": txn.user_id,
                    "user_email": txn.user.email if txn.user else None,
                    "amount": txn.amount,
                    "currency": txn.currency,
                    "status": txn.status,
                    "provider": txn.provider,
                    "provider_transaction_id": txn.provider_transaction_id,
                    "created_at": txn.created_at.isoformat() if txn.created_at else None,
                    "updated_at": txn.updated_at.isoformat() if txn.updated_at else None,
                }
                for txn in items
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }
    )


@admin_bp.route("/usage/heroku", methods=["GET"])
def heroku_usage():
    _, error = _require_admin()
    if error:
        return error
    return jsonify(stats.heroku_usage())


@admin_bp.route("/usage/bandwidth", methods=["GET"])
def bandwidth_usage():
    _, error = _require_admin()
    if error:
        return error
    from_date = request.args.get("from")
    to_date = request.args.get("to")
    if not from_date or not to_date:
        return jsonify({"ok": False, "error": "INVALID_RANGE"}), 400
    start = datetime.fromisoformat(from_date).date()
    end = datetime.fromisoformat(to_date).date()
    points = stats.bandwidth_points(start, end)
    return jsonify({"points": points})
