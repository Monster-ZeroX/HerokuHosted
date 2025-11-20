from webapp.models import EmailOTP, User


def test_registration_otp_flow(client):
    res = client.post(
        "/api/auth/register/start",
        json={"username": "alice", "email": "alice@example.com", "password": "pw"},
    )
    assert res.status_code == 200
    assert res.get_json()["ok"]
    with client.application.app_context():
        otp = EmailOTP.query.filter_by(email="alice@example.com", purpose="registration").first()
    assert otp is not None

    res = client.post("/api/auth/register/verify", json={"email": "alice@example.com", "code": otp.code})
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"]
    assert data["user"]["plan"]["type"] == "free"
    with client.application.app_context():
        assert User.query.filter_by(email="alice@example.com").first() is not None


def test_password_reset_otp(client):
    # create user
    client.post(
        "/api/auth/register/start",
        json={"username": "bob", "email": "bob@example.com", "password": "pw"},
    )
    with client.application.app_context():
        otp = EmailOTP.query.filter_by(email="bob@example.com", purpose="registration").first()
    client.post("/api/auth/register/verify", json={"email": "bob@example.com", "code": otp.code})

    res = client.post("/api/auth/password-reset/start", json={"email": "bob@example.com"})
    assert res.status_code == 200
    with client.application.app_context():
        reset_otp = EmailOTP.query.filter_by(email="bob@example.com", purpose="password_reset").first()
    assert reset_otp is not None

    res = client.post(
        "/api/auth/password-reset/complete",
        json={"email": "bob@example.com", "code": reset_otp.code, "new_password": "new"},
    )
    assert res.status_code == 200
    assert res.get_json()["ok"]
