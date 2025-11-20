from __future__ import annotations

from flask import Blueprint, request, jsonify, session

from webapp.services.torrent_service import TorrentService
from webapp.services.auth_service import AuthService
from webapp.models import User


torrents_bp = Blueprint("torrents", __name__)
service = TorrentService()
auth = AuthService()


def _current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def _require_auth():
    user = _current_user()
    if not user:
        return None, (jsonify({"ok": False, "error": "AUTH_REQUIRED"}), 401)
    return user, None


def _pagination():
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    return page, page_size


@torrents_bp.route("", methods=["GET"])
def list_jobs():
    user, error = _require_auth()
    if error:
        return error
    status = request.args.get("status")
    source_type = request.args.get("source_type")
    page, page_size = _pagination()
    items, total = service.list_jobs(user, status, source_type, page, page_size)
    return jsonify(
        {
            "items": [job.to_dict() for job in items],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }
    )


@torrents_bp.route("", methods=["POST"])
def create_job():
    user, error = _require_auth()
    if error:
        return error
    if not request.is_json:
        return jsonify({"ok": False, "error": "INVALID_JSON"}), 400
    payload = request.get_json() or {}
    result = service.create_job(user, payload)
    status_code = 200 if result.get("ok") else 400
    return jsonify(result), status_code


@torrents_bp.route("/<int:job_id>", methods=["GET"])
def get_job(job_id: int):
    user, error = _require_auth()
    if error:
        return error
    job = service.get_job(user, job_id)
    if not job:
        return jsonify({"ok": False, "error": "NOT_FOUND"}), 404
    return jsonify({"job": job.to_dict()})


@torrents_bp.route("/<int:job_id>/cancel", methods=["POST"])
def cancel_job(job_id: int):
    user, error = _require_auth()
    if error:
        return error
    job = service.get_job(user, job_id)
    if not job:
        return jsonify({"ok": False, "error": "NOT_FOUND"}), 404
    return jsonify(service.cancel_job(job))
