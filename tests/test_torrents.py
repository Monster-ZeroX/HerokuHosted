from webapp.models import User, TransferJob
from webapp.services.torrent_service import TorrentService


def create_user(email: str, daily_limit_gb: float = 1.0):
    user = User(username=email.split('@')[0], email=email, plan_type="free", daily_limit_gb=daily_limit_gb)
    user.set_password("pw")
    return user


def test_daily_limit_enforced(app, client):
    with app.app_context():
        user = create_user("limit@example.com", daily_limit_gb=1)
        from webapp.models import db

        db.session.add(user)
        db.session.commit()

        client.post("/api/auth/login", json={"email_or_username": user.email, "password": "pw"})
        res = client.post(
            "/api/torrents",
            json={"source_type": "torrent", "magnet_link": "magnet:?", "save_folder": "f", "size_bytes": 3 * 1024 ** 3},
        )
        assert res.status_code == 400
        assert res.get_json()["error"] == "DAILY_LIMIT_EXCEEDED"


def test_status_transitions(app, client):
    with app.app_context():
        user = create_user("status@example.com", daily_limit_gb=5)
        from webapp.models import db

        db.session.add(user)
        db.session.commit()
        client.post("/api/auth/login", json={"email_or_username": user.email, "password": "pw"})

        res = client.post("/api/torrents", json={"source_type": "torrent", "magnet_link": "m", "save_folder": "folder"})
        job_id = res.get_json()["job"]["id"]
        job = TransferJob.query.get(job_id)
        service = TorrentService()
        service.transition(job, "downloading", progress=10)
        service.transition(job, "completed", progress=100)
        db.session.refresh(job)
        assert job.status == "completed"
        assert job.completed_at is not None
