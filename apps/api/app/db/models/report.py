"""Report, versions, and taxonomy (categories, tags, technologies)."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class ReportStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class Visibility(str, enum.Enum):
    public = "public"
    internal = "internal"
    private = "private"


# --- association tables ---------------------------------------------------
report_tags = Table(
    "report_tags",
    Base.metadata,
    Column("report_id", ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

report_technologies = Table(
    "report_technologies",
    Base.metadata,
    Column("report_id", ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True),
    Column("technology_id", ForeignKey("technologies.id", ondelete="CASCADE"), primary_key=True),
)


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    reports: Mapped[list[Report]] = relationship(back_populates="category")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    reports: Mapped[list[Report]] = relationship(secondary=report_tags, back_populates="tags")


class Technology(Base):
    __tablename__ = "technologies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    reports: Mapped[list[Report]] = relationship(
        secondary=report_technologies, back_populates="technologies"
    )


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(340), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Plain text of the latest HTML version, kept here so FTS can search inside content.
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    team: Mapped[str | None] = mapped_column(String(120), nullable=True)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    project: Mapped[str | None] = mapped_column(String(200), nullable=True)

    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status"), default=ReportStatus.draft, nullable=False
    )
    visibility: Mapped[Visibility] = mapped_column(
        Enum(Visibility, name="visibility"), default=Visibility.internal, nullable=False
    )
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # external links / metadata
    github_repo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pull_request: Mapped[str | None] = mapped_column(String(500), nullable=True)
    demo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Postgres full-text search vector (maintained via trigger; see migration)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    # relationships
    author: Mapped[User] = relationship(back_populates="reports")
    category: Mapped[Category | None] = relationship(back_populates="reports")
    tags: Mapped[list[Tag]] = relationship(secondary=report_tags, back_populates="reports")
    technologies: Mapped[list[Technology]] = relationship(
        secondary=report_technologies, back_populates="reports"
    )
    versions: Mapped[list[ReportVersion]] = relationship(
        back_populates="report", cascade="all, delete-orphan", order_by="ReportVersion.version"
    )


class ReportVersion(Base, TimestampMixin):
    __tablename__ = "report_versions"
    __table_args__ = (UniqueConstraint("report_id", "version", name="uq_report_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    html_blob_path: Mapped[str | None] = mapped_column(String(600), nullable=True)
    pdf_blob_path: Mapped[str | None] = mapped_column(String(600), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # for FTS
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    report: Mapped[Report] = relationship(back_populates="versions")
