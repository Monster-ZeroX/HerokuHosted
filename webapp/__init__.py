"""Web application package factory."""
from .app_factory import create_app
from .models import db

__all__ = ["create_app", "db"]
