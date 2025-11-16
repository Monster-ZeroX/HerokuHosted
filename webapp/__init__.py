"""Web application package."""
from webapp.app import app
from webapp.models import db

__all__ = ["app", "db"]
