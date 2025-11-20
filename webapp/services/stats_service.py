"""Aggregated statistics for admin dashboards."""
from __future__ import annotations

from datetime import datetime, date
from typing import List

from sqlalchemy import func, case

from webapp.models import db, User, TransferJob, Transaction


class StatsService:
    def __init__(self):
        pass

    def overview(self) -> dict:
        total = User.query.count()
        free = User.query.filter(User.plan_type == "free").count()
        paid = User.query.filter(User.plan_type == "paid").count()
        active_jobs_free = TransferJob.query.filter(TransferJob.app_role == "FREE", TransferJob.status.in_(["queued", "downloading", "uploading"])).count()
        active_jobs_paid = TransferJob.query.filter(TransferJob.app_role == "PAID", TransferJob.status.in_(["queued", "downloading", "uploading"])).count()
        today = date.today()
        bandwidth_free = db.session.query(func.coalesce(func.sum(TransferJob.size_bytes), 0)).filter(TransferJob.app_role == "FREE", func.date(TransferJob.completed_at) == today).scalar() or 0
        bandwidth_paid = db.session.query(func.coalesce(func.sum(TransferJob.size_bytes), 0)).filter(TransferJob.app_role == "PAID", func.date(TransferJob.completed_at) == today).scalar() or 0
        return {
            "user_counts": {"total": total, "free": free, "paid": paid},
            "active_jobs": {"free": active_jobs_free, "paid": active_jobs_paid},
            "bandwidth_today_gb": {
                "total": round((bandwidth_free + bandwidth_paid) / (1024 ** 3), 2),
                "free": round(bandwidth_free / (1024 ** 3), 2),
                "paid": round(bandwidth_paid / (1024 ** 3), 2),
            },
        }

    def heroku_usage(self):
        today = date.today()
        free_rows = (
            db.session.query(
                TransferJob.app_instance,
                func.count(TransferJob.id),
                func.coalesce(func.sum(TransferJob.size_bytes), 0),
            )
            .filter(TransferJob.app_role == "FREE", func.date(TransferJob.completed_at) == today)
            .group_by(TransferJob.app_instance)
            .all()
        )
        paid_row = (
            db.session.query(
                TransferJob.app_instance,
                func.count(TransferJob.id),
                func.coalesce(func.sum(TransferJob.size_bytes), 0),
            )
            .filter(TransferJob.app_role == "PAID", func.date(TransferJob.completed_at) == today)
            .group_by(TransferJob.app_instance)
            .first()
        )
        total_bandwidth = sum(r[2] for r in free_rows) + (paid_row[2] if paid_row else 0)
        return {
            "free_apps": [
                {
                    "app_instance": row[0],
                    "jobs_completed_today": row[1],
                    "bandwidth_today_gb": round(row[2] / (1024 ** 3), 2),
                }
                for row in free_rows
            ],
            "paid_app": paid_row
            and {
                "app_instance": paid_row[0],
                "jobs_completed_today": paid_row[1],
                "bandwidth_today_gb": round(paid_row[2] / (1024 ** 3), 2),
            },
            "total_bandwidth_today_gb": round(total_bandwidth / (1024 ** 3), 2),
        }

    def bandwidth_points(self, start: date, end: date):
        rows = (
            db.session.query(
                func.date(TransferJob.completed_at),
                func.coalesce(func.sum(TransferJob.size_bytes), 0),
                func.coalesce(
                    func.sum(case((TransferJob.app_role == "FREE", TransferJob.size_bytes), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(case((TransferJob.app_role == "PAID", TransferJob.size_bytes), else_=0)), 0
                ),
            )
            .filter(TransferJob.completed_at >= start, TransferJob.completed_at <= end)
            .group_by(func.date(TransferJob.completed_at))
            .order_by(func.date(TransferJob.completed_at))
            .all()
        )
        return [
            {
                "date": row[0].isoformat(),
                "total_gb": round(row[1] / (1024 ** 3), 2),
                "free_gb": round(row[2] / (1024 ** 3), 2),
                "paid_gb": round(row[3] / (1024 ** 3), 2),
            }
            for row in rows
        ]
