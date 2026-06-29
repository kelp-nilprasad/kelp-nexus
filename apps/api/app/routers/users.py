"""User/author profiles."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.models.report import Report
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.report import ReportSummary
from app.schemas.user import UserPublic, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserPublic])
def list_authors(db: Session = Depends(get_db)):
    """Users who have authored at least one report — powers the author filter."""
    return db.scalars(
        select(User)
        .where(User.id.in_(select(Report.author_id).distinct()))
        .order_by(User.name)
    ).all()


@router.get("/{user_id}", response_model=UserPublic)
def get_profile(user_id: uuid.UUID, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.get("/{user_id}/reports", response_model=list[ReportSummary])
def user_reports(user_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.scalars(
        select(Report).where(Report.author_id == user_id)
        .options(
            selectinload(Report.author), selectinload(Report.category),
            selectinload(Report.tags), selectinload(Report.technologies),
        )
        .order_by(Report.created_at.desc())
    ).all()


@router.patch("/me", response_model=UserPublic)
def update_me(
    payload: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user
