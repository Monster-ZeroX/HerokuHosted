"""Flask application factory for DirectTorrent.me."""
from __future__ import annotations

import os
from datetime import timedelta
from flask import Flask, jsonify, request

from .models import db


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///directtorrent.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE=os.environ.get("SESSION_COOKIE_SAMESITE", "None"),
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "true").lower()
        in {"1", "true", "yes"},
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    )

    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
        app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace(
            "postgres://", "postgresql://"
        )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    @app.after_request
    def add_cors_headers(response):
        allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
        origin = request.headers.get("Origin")
        if allowed_origins == "*" or (origin and origin in allowed_origins.split(",")):
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,PATCH,OPTIONS"
        return response

    with app.app_context():
        db.create_all()

    from .api import register_blueprints

    register_blueprints(app)

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"ok": False, "error": "NOT_FOUND"}), 404

    return app
