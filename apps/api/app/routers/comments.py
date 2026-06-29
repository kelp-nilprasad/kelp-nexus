"""Threaded comments on reports."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.models.engagement import Comment
from app.db.models.report import Report
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.engagement import CommentCreate, CommentOut

router = APIRouter(tags=["comments"])


@router.get("/reports/{report_id}/comments", response_model=list[CommentOut])
def list_comments(report_id: uuid.UUID, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Comment)
        .where(Comment.report_id == report_id, Comment.parent_id.is_(None))
        .options(selectinload(Comment.author), selectinload(Comment.replies).selectinload(Comment.author))
        .order_by(Comment.created_at.asc())
    ).all()
    return rows


@router.post("/reports/{report_id}/comments", response_model=CommentOut, status_code=201)
def create_comment(
    report_id: uuid.UUID,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not db.get(Report, report_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    comment = Comment(
        report_id=report_id, author_id=user.id, parent_id=payload.parent_id, body=payload.body
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found")
    if comment.author_id != user.id and user.role not in (Role.admin, Role.editor):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot delete this comment")
    db.delete(comment)
    db.commit()
