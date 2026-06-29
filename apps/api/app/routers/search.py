"""Search endpoints (FTS now; semantic toggle reserved for AI phase)."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models.report import ReportStatus, Visibility
from app.db.session import get_db
from app.schemas.engagement import SearchResponse, SearchResult
from app.schemas.report import ReportSummary
from pydantic import BaseModel

from app.services.search import full_text_search, suggest

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="keyword query"),
    category_id: uuid.UUID | None = None,
    tag: str | None = None,
    technology: str | None = None,
    author_id: uuid.UUID | None = None,
    project: str | None = None,
    status: ReportStatus | None = None,
    visibility: Visibility | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    results, total = full_text_search(
        db, q, category_id=category_id, tag=tag, technology=technology,
        author_id=author_id, project=project, status=status, visibility=visibility,
        date_from=date_from, date_to=date_to, page=page, page_size=page_size,
    )
    return SearchResponse(
        items=[
            SearchResult(report=ReportSummary.model_validate(r), rank=rank)
            for r, rank in results
        ],
        total=total, query=q or "", semantic=False,
    )


class Suggestion(BaseModel):
    label: str
    type: str  # "technology" | "tag" | "report"
    value: str  # slug to navigate / filter by


@router.get("/suggest", response_model=list[Suggestion])
def search_suggest(
    db: Session = Depends(get_db),
    q: str = Query("", description="prefix typed so far"),
    limit: int = Query(8, ge=1, le=20),
):
    """Autocomplete: prefix-match technologies/tags and report titles as you type."""
    return [Suggestion(**s) for s in suggest(db, q, limit=limit)]
