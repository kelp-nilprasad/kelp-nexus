"""Favorites + recently-viewed for the current user."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.models.engagement import Favorite, RecentlyViewed
from app.db.models.report import Report
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.report import ReportSummary

router = APIRouter(tags=["favorites"])

_EAGER = (
    selectinload(Report.author), selectinload(Report.category),
    selectinload(Report.tags), selectinload(Report.technologies),
)


@router.get("/favorites", response_model=list[ReportSummary])
def list_favorites(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(
        select(Report).join(Favorite, Favorite.report_id == Report.id)
        .where(Favorite.user_id == user.id).options(*_EAGER)
        .order_by(Favorite.created_at.desc())
    ).all()
    return rows


@router.put("/reports/{report_id}/favorite", status_code=204)
def add_favorite(
    report_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if not db.get(Report, report_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    exists = db.scalar(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.report_id == report_id)
    )
    if not exists:
        db.add(Favorite(user_id=user.id, report_id=report_id))
        db.commit()


@router.delete("/reports/{report_id}/favorite", status_code=204)
def remove_favorite(
    report_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    fav = db.scalar(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.report_id == report_id)
    )
    if fav:
        db.delete(fav)
        db.commit()


@router.get("/recently-viewed", response_model=list[ReportSummary])
def recently_viewed(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(
        select(Report).join(RecentlyViewed, RecentlyViewed.report_id == Report.id)
        .where(RecentlyViewed.user_id == user.id).options(*_EAGER)
        .order_by(RecentlyViewed.viewed_at.desc()).limit(20)
    ).all()
    return rows
