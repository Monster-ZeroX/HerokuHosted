"""Placeholder Mega service layer."""
from __future__ import annotations

from typing import Optional


class MegaService:
    def __init__(self):
        pass

    def validate_link(self, link: str) -> bool:
        return bool(link and "mega.nz" in link)
