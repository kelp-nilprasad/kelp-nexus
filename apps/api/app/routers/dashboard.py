"""Dashboard aggregates + analytics."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.engagement import Comment, ReportView
from app.db.models.report import Category, Report, ReportStatus
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.report import ReportSummary

router = APIRouter(tags=["dashboard"])

_EAGER = (
    selectinload(Report.author), selectinload(Report.category),
    selectinload(Report.tags), selectinload(Report.technologies),
)


def _published(stmt):
    return stmt.where(Report.status == ReportStatus.published)


class RecentComment(BaseModel):
    report_id: str
    report_title: str
    report_slug: str
    author_name: str
    body: str
    created_at: datetime


class DashboardResponse(BaseModel):
    recently_added: list[ReportSummary]
    recently_updated: list[ReportSummary]
    trending: list[ReportSummary]
    most_viewed: list[ReportSummary]
    recent_comments: list[RecentComment]
    category_counts: dict[str, int]


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db)):
    recently_added = db.scalars(
        _published(select(Report)).options(*_EAGER).order_by(Report.created_at.desc()).limit(8)
    ).all()
    recently_updated = db.scalars(
        _published(select(Report)).options(*_EAGER).order_by(Report.updated_at.desc()).limit(8)
    ).all()
    most_viewed = db.scalars(
        _published(select(Report)).options(*_EAGER).order_by(Report.view_count.desc()).limit(8)
    ).all()

    # trending = most views in the last 7 days
    since = datetime.now(timezone.utc) - timedelta(days=7)
    trending_ids = db.execute(
        select(ReportView.report_id, func.count().label("c"))
        .where(ReportView.viewed_at >= since)
        .group_by(ReportView.report_id).order_by(func.count().desc()).limit(8)
    ).all()
    id_order = [rid for rid, _ in trending_ids]
    trending = []
    if id_order:
        found = db.scalars(
            select(Report).where(Report.id.in_(id_order)).options(*_EAGER)
        ).all()
        by_id = {r.id: r for r in found}
        trending = [by_id[i] for i in id_order if i in by_id]

    recent_comments_rows = db.scalars(
        select(Comment).options(selectinload(Comment.author), selectinload(Comment.report))
        .order_by(Comment.created_at.desc()).limit(8)
    ).all()
    recent_comments = [
        RecentComment(
            report_id=str(c.report_id), report_title=c.report.title, report_slug=c.report.slug,
            author_name=c.author.name, body=c.body, created_at=c.created_at,
        )
        for c in recent_comments_rows
    ]

    cat_rows = db.execute(
        select(Category.name, func.count(Report.id))
        .outerjoin(Report, Report.category_id == Category.id)
        .group_by(Category.name)
    ).all()

    return DashboardResponse(
        recently_added=[ReportSummary.model_validate(r) for r in recently_added],
        recently_updated=[ReportSummary.model_validate(r) for r in recently_updated],
        trending=[ReportSummary.model_validate(r) for r in trending],
        most_viewed=[ReportSummary.model_validate(r) for r in most_viewed],
        recent_comments=recent_comments,
        category_counts={name: count for name, count in cat_rows},
    )


class AnalyticsResponse(BaseModel):
    total_reports: int
    total_published: int
    total_users: int
    total_views: int
    views_last_30d: int
    top_authors: list[dict]


@router.get("/analytics", response_model=AnalyticsResponse)
def analytics(db: Session = Depends(get_db)):
    total_reports = db.scalar(select(func.count(Report.id))) or 0
    total_published = db.scalar(
        select(func.count(Report.id)).where(Report.status == ReportStatus.published)
    ) or 0
    total_users = db.scalar(select(func.count(User.id))) or 0
    total_views = db.scalar(select(func.coalesce(func.sum(Report.view_count), 0))) or 0
    since = datetime.now(timezone.utc) - timedelta(days=30)
    views_30 = db.scalar(
        select(func.count(ReportView.id)).where(ReportView.viewed_at >= since)
    ) or 0
    top_authors_rows = db.execute(
        select(User.name, func.count(Report.id).label("c"))
        .join(Report, Report.author_id == User.id)
        .group_by(User.id).order_by(func.count(Report.id).desc()).limit(5)
    ).all()
    return AnalyticsResponse(
        total_reports=total_reports, total_published=total_published, total_users=total_users,
        total_views=int(total_views), views_last_30d=views_30,
        top_authors=[{"name": n, "reports": c} for n, c in top_authors_rows],
    )
