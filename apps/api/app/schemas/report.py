"""Report + taxonomy Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.db.models.report import ReportStatus, Visibility
from app.schemas.user import UserPublic


class TaxonomyItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    slug: str


class CategoryOut(TaxonomyItem):
    description: str | None = None
    parent_id: uuid.UUID | None = None


class ReportBase(BaseModel):
    title: str
    description: str | None = None
    summary: str | None = None
    team: str | None = None
    department: str | None = None
    project: str | None = None
    status: ReportStatus = ReportStatus.draft
    visibility: Visibility = Visibility.internal
    github_repo: str | None = None
    pull_request: str | None = None
    demo_url: str | None = None
    video_url: str | None = None


class ReportCreate(ReportBase):
    category_id: uuid.UUID | None = None
    tags: list[str] = []
    technologies: list[str] = []

    @model_validator(mode="after")
    def _require_fields(self) -> "ReportCreate":
        missing = []
        if not (self.description or "").strip():
            missing.append("description")
        if not (self.summary or "").strip():
            missing.append("summary")
        if not [t for t in self.tags if t and t.strip()]:
            missing.append("tags")
        if missing:
            raise ValueError(f"Required: {', '.join(missing)}")
        return self


class ReportUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    summary: str | None = None
    team: str | None = None
    department: str | None = None
    project: str | None = None
    status: ReportStatus | None = None
    visibility: Visibility | None = None
    category_id: uuid.UUID | None = None
    github_repo: str | None = None
    pull_request: str | None = None
    demo_url: str | None = None
    video_url: str | None = None
    tags: list[str] | None = None
    technologies: list[str] | None = None


class ReportVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    version: int
    changelog: str | None = None
    created_at: datetime
    has_html: bool = False
    has_pdf: bool = False


class ReportSummary(BaseModel):
    """Lightweight shape for lists / cards."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    slug: str
    summary: str | None = None
    description: str | None = None
    status: ReportStatus
    visibility: Visibility
    view_count: int
    current_version: int
    created_at: datetime
    updated_at: datetime
    author: UserPublic
    category: CategoryOut | None = None
    tags: list[TaxonomyItem] = []
    technologies: list[TaxonomyItem] = []


class ReportDetail(ReportSummary):
    team: str | None = None
    department: str | None = None
    project: str | None = None
    github_repo: str | None = None
    pull_request: str | None = None
    demo_url: str | None = None
    video_url: str | None = None
    versions: list[ReportVersionOut] = []


class PaginatedReports(BaseModel):
    items: list[ReportSummary]
    total: int
    page: int
    page_size: int
