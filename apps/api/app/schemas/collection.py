"""Collection Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.report import ReportSummary
from app.schemas.user import UserPublic


class CollectionCreate(BaseModel):
    name: str
    description: str | None = None
    is_public: bool = True
    parent_id: uuid.UUID | None = None


class CollectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None
    parent_id: uuid.UUID | None = None


class Breadcrumb(BaseModel):
    id: uuid.UUID
    name: str
    slug: str


class CollectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    is_public: bool
    parent_id: uuid.UUID | None = None
    owner: UserPublic
    created_at: datetime
    report_count: int = 0
    subfolder_count: int = 0


class CollectionDetail(CollectionOut):
    reports: list[ReportSummary] = []
    children: list[CollectionOut] = []
    breadcrumbs: list[Breadcrumb] = []
