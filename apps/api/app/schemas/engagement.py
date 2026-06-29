"""Comments, favorites, search Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.report import ReportSummary
from app.schemas.user import UserPublic


class CommentCreate(BaseModel):
    body: str
    parent_id: uuid.UUID | None = None


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    body: str
    created_at: datetime
    author: UserPublic
    parent_id: uuid.UUID | None = None
    replies: list["CommentOut"] = []


class SearchResult(BaseModel):
    report: ReportSummary
    rank: float
    snippet: str | None = None


class SearchResponse(BaseModel):
    items: list[SearchResult]
    total: int
    query: str
    semantic: bool = False
