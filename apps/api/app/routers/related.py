"""Related reports (metadata-based now; swappable for embeddings later)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.report import Report, ReportStatus, report_tags, report_technologies
from app.db.session import get_db
from app.schemas.report import ReportSummary

router = APIRouter(tags=["related"])


@router.get("/reports/{slug_or_id}/related", response_model=list[ReportSummary])
def related_reports(slug_or_id: str, db: Session = Depends(get_db), limit: int = 6):
    """Score other reports by shared tags + technologies + category."""
    import uuid

    stmt = select(Report)
    try:
        stmt = stmt.where(Report.id == uuid.UUID(slug_or_id))
    except ValueError:
        stmt = stmt.where(Report.slug == slug_or_id)
    report = db.scalar(stmt)
    if not report:
        return []

    tag_ids = [t.id for t in report.tags]
    tech_ids = [t.id for t in report.technologies]

    score = func.count().label("score")
    candidates = (
        select(Report.id, score)
        .outerjoin(report_tags, report_tags.c.report_id == Report.id)
        .outerjoin(report_technologies, report_technologies.c.report_id == Report.id)
        .where(Report.id != report.id, Report.status == ReportStatus.published)
        .where(
            (report_tags.c.tag_id.in_(tag_ids) if tag_ids else False)
            | (report_technologies.c.technology_id.in_(tech_ids) if tech_ids else False)
            | (Report.category_id == report.category_id if report.category_id else False)
        )
        .group_by(Report.id)
        .order_by(score.desc())
        .limit(limit)
    )
    rows = db.execute(candidates).all()
    ids = [rid for rid, _ in rows]
    if not ids:
        return []
    reports = db.scalars(
        select(Report).where(Report.id.in_(ids)).options(
            selectinload(Report.author), selectinload(Report.category),
            selectinload(Report.tags), selectinload(Report.technologies),
        )
    ).all()
    by_id = {r.id: r for r in reports}
    return [by_id[i] for i in ids if i in by_id]
