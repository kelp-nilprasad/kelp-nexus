"""Compatibility shim.

Some modules import `from app.settings import get_settings`; the canonical
location is `app.core.config`. Re-export here so both paths work.
"""
from app.core.config import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]
