"""Compatibility shim pointing to the new application factory."""
from webapp.app_factory import create_app

app = create_app()

__all__ = ["app", "create_app"]
