"""API blueprint registration."""
from flask import Flask

from .auth import auth_bp
from .torrents import torrents_bp
from .admin import admin_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(torrents_bp, url_prefix="/api/torrents")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
