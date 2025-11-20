"""Torrent and Mega job handling."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from webapp.models import db, TransferJob, User


class TorrentService:
    def __init__(self):
        self.app_role = os.environ.get("APP_ROLE", "FREE").upper()
        self.app_instance = os.environ.get("HEROKU_APP_NAME") or os.environ.get("APP_INSTANCE") or "directtorrent-local"

    def list_jobs(self, user: User, status: Optional[str], source_type: Optional[str], page: int, page_size: int):
        query = TransferJob.query.filter_by(user_id=user.id)
        if status:
            query = query.filter(TransferJob.status == status)
        if source_type:
            query = query.filter(TransferJob.source_type == source_type)
        total = query.count()
        items = query.order_by(TransferJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def _check_limit(self, user: User, size_bytes: int) -> bool:
        return user.has_capacity(size_bytes)

    def create_job(self, user: User, payload: dict) -> dict:
        source_type = payload.get("source_type")
        if source_type not in ("torrent", "mega"):
            return {"ok": False, "error": "INVALID_SOURCE"}

        size_bytes = int(payload.get("size_bytes") or 0)
        if not self._check_limit(user, size_bytes):
            return {"ok": False, "error": "DAILY_LIMIT_EXCEEDED"}

        name = payload.get("name") or payload.get("magnet_link") or payload.get("source_url")
        job = TransferJob(
            user_id=user.id,
            name=name,
            source_type=source_type,
            magnet_link=payload.get("magnet_link"),
            source_url=payload.get("source_url"),
            status="queued",
            size_bytes=size_bytes or None,
            app_role=self.app_role,
            app_instance=self.app_instance,
        )
        db.session.add(job)
        user.add_usage(size_bytes)
        db.session.commit()
        return {"ok": True, "job": job.to_dict()}

    def get_job(self, user: User, job_id: int) -> Optional[TransferJob]:
        return TransferJob.query.filter_by(id=job_id, user_id=user.id).first()

    def cancel_job(self, job: TransferJob) -> dict:
        if job.status in {"completed", "failed", "canceled"}:
            return {"ok": True, "job": job.to_dict()}
        job.status = "canceled"
        job.completed_at = datetime.utcnow()
        db.session.commit()
        return {"ok": True, "job": job.to_dict()}

    def transition(self, job: TransferJob, status: str, progress: float = None) -> TransferJob:
        job.status = status
        if progress is not None:
            job.progress = progress
        if status == "completed":
            job.completed_at = datetime.utcnow()
        db.session.commit()
        return job
