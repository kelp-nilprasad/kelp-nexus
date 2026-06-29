"""Aggregate model imports so Alembic + SQLAlchemy see every table."""
from app.db.models.user import User
from app.db.models.report import (
    Category,
    Report,
    ReportVersion,
    Tag,
    Technology,
    report_tags,
    report_technologies,
)
from app.db.models.engagement import Comment, Favorite, RecentlyViewed, ReportView
from app.db.models.collection import Collection, collection_reports
from app.db.models.ai import Embedding
from app.db.models.audit import AuditLog

__all__ = [
    "User",
    "Category",
    "Report",
    "ReportVersion",
    "Tag",
    "Technology",
    "report_tags",
    "report_technologies",
    "Comment",
    "Favorite",
    "RecentlyViewed",
    "ReportView",
    "Collection",
    "collection_reports",
    "Embedding",
    "AuditLog",
]
