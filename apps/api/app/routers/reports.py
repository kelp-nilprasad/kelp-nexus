"""Report CRUD, HTML/PDF upload, versioning, and rendering."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.deps import get_current_user, get_optional_user, require_role
from app.db.models.report import Report, ReportStatus, ReportVersion, Visibility
from app.db.models.user import Role, User
from app.db.models.engagement import RecentlyViewed, ReportView
from app.db.session import get_db
from app.schemas.report import (
    PaginatedReports,
    ReportCreate,
    ReportDetail,
    ReportSummary,
    ReportUpdate,
    ReportVersionOut,
)
from app.services.ai import generate_summary, generate_tags
from app.services.html_sanitize import extract_text, sanitize_html
from app.services.storage import get_storage
from app.services.taxonomy import unique_report_slug, upsert_tags, upsert_technologies

router = APIRouter(prefix="/reports", tags=["reports"])
logger = logging.getLogger(__name__)

_EAGER = (
    selectinload(Report.author),
    selectinload(Report.category),
    selectinload(Report.tags),
    selectinload(Report.technologies),
    selectinload(Report.versions),
)


def _get_or_404(db: Session, slug_or_id: str) -> Report:
    stmt = select(Report).options(*_EAGER)
    try:
        rid = uuid.UUID(slug_or_id)
        stmt = stmt.where(Report.id == rid)
    except ValueError:
        stmt = stmt.where(Report.slug == slug_or_id)
    report = db.scalar(stmt)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return report


def _detail(report: Report) -> ReportDetail:
    detail = ReportDetail.model_validate(report)
    detail.versions = [
        ReportVersionOut(
            id=v.id, version=v.version, changelog=v.changelog, created_at=v.created_at,
            has_html=bool(v.html_blob_path), has_pdf=bool(v.pdf_blob_path),
        )
        for v in report.versions
    ]
    return detail


@router.get("", response_model=PaginatedReports)
def list_reports(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: ReportStatus | None = Query(None, alias="status"),
):
    stmt = select(Report).options(*_EAGER)
    if status_filter:
        stmt = stmt.where(Report.status == status_filter)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(Report.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
    ).scalars().all()
    return PaginatedReports(
        items=[ReportSummary.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
    )


@router.post("", response_model=ReportDetail, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(Role.author)),
):
    report = Report(
        **payload.model_dump(exclude={"tags", "technologies", "category_id"}),
        category_id=payload.category_id,
        author_id=user.id,
        slug=unique_report_slug(db, payload.title),
    )
    db.add(report)
    db.flush()  # ensure report is in the session before wiring associations
    report.tags = upsert_tags(db, payload.tags)
    report.technologies = upsert_technologies(db, payload.technologies)
    db.commit()
    db.refresh(report)
    return _detail(_get_or_404(db, str(report.id)))


@router.get("/{slug_or_id}", response_model=ReportDetail)
def get_report(
    slug_or_id: str,
    response: Response,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    report = _get_or_404(db, slug_or_id)
    if report.visibility == Visibility.private and (not user or user.id != report.author_id):
        if not user or user.role != Role.admin:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This report is private")
    # track the view
    report.view_count += 1
    db.add(ReportView(report_id=report.id, user_id=user.id if user else None))
    if user:
        rv = db.scalar(
            select(RecentlyViewed).where(
                RecentlyViewed.user_id == user.id, RecentlyViewed.report_id == report.id
            )
        )
        if rv is None:
            db.add(RecentlyViewed(user_id=user.id, report_id=report.id))
    db.commit()
    db.refresh(report)
    return _detail(report)


@router.patch("/{slug_or_id}", response_model=ReportDetail)
def update_report(
    slug_or_id: str,
    payload: ReportUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = _get_or_404(db, slug_or_id)
    if report.author_id != user.id and user.role not in (Role.admin, Role.editor):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot edit this report")
    data = payload.model_dump(exclude_unset=True, exclude={"tags", "technologies"})
    for k, v in data.items():
        setattr(report, k, v)
    if payload.tags is not None:
        report.tags = upsert_tags(db, payload.tags)
    if payload.technologies is not None:
        report.technologies = upsert_technologies(db, payload.technologies)
    db.commit()
    db.refresh(report)
    return _detail(report)


@router.delete("/{slug_or_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    slug_or_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = _get_or_404(db, slug_or_id)
    if report.author_id != user.id and user.role != Role.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot delete this report")
    db.delete(report)
    db.commit()


@router.post("/{slug_or_id}/versions", response_model=ReportVersionOut)
async def upload_version(
    slug_or_id: str,
    html: UploadFile | None = File(None),
    pdf: UploadFile | None = File(None),
    changelog: str | None = Form(None),
    auto_summarize: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload an HTML report and/or PDF as a new version (sanitized on ingest)."""
    report = _get_or_404(db, slug_or_id)
    if report.author_id != user.id and user.role not in (Role.admin, Role.editor):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot add a version")
    if not html and not pdf:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide an HTML and/or PDF file")

    storage = get_storage()
    new_version = report.current_version + 1 if report.versions else 1
    html_path = pdf_path = None
    extracted = None

    if html:
        raw = (await html.read()).decode("utf-8", errors="replace")
        clean = sanitize_html(raw)
        extracted = extract_text(clean)
        report.content_text = extracted  # feeds the FTS trigger
        html_path = storage.upload(
            f"reports/{report.id}/v{new_version}/report.html",
            clean.encode("utf-8"), "text/html; charset=utf-8",
        )
        if auto_summarize:
            summary = generate_summary(extracted)
            if summary:
                report.summary = summary
            ai_tags = generate_tags(extracted)
            if ai_tags:
                report.tags = upsert_tags(db, [t.name for t in report.tags] + ai_tags)

    if pdf:
        pdf_path = storage.upload(
            f"reports/{report.id}/v{new_version}/report.pdf",
            await pdf.read(), "application/pdf",
        )

    version = ReportVersion(
        report_id=report.id, version=new_version, html_blob_path=html_path,
        pdf_blob_path=pdf_path, extracted_text=extracted, changelog=changelog,
        created_by=user.id,
    )
    db.add(version)
    report.current_version = new_version
    db.commit()
    db.refresh(version)
    return ReportVersionOut(
        id=version.id, version=version.version, changelog=version.changelog,
        created_at=version.created_at, has_html=bool(html_path), has_pdf=bool(pdf_path),
    )


@router.get("/{slug_or_id}/render", response_class=Response)
def render_html(
    slug_or_id: str,
    version: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """Return sanitized HTML for the report. Served into a sandboxed iframe by the web app."""
    report = _get_or_404(db, slug_or_id)
    target = None
    for v in sorted(report.versions, key=lambda x: x.version, reverse=True):
        if (version is None or v.version == version) and v.html_blob_path:
            target = v
            break
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No HTML for this report/version")
    try:
        data = get_storage().download(target.html_blob_path)
    except Exception as exc:  # blob missing / storage unreachable
        # Surface a clear error instead of an opaque 500 rendered inside the iframe.
        logger.exception(
            "Failed to load report HTML blob %s (report %s): %s",
            target.html_blob_path, report.id, exc,
        )
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Report content is unavailable (could not read it from storage).",
        ) from exc
    # Lock down rendering; this endpoint is loaded by an isolated sandboxed iframe.
    # frame-ancestors must list the web origin(s) or the browser blocks the frame
    # in production (localhost only works in dev).
    frame_ancestors = " ".join(settings.cors_origins) or "'self'"
    headers = {
        "Content-Security-Policy": (
            "default-src 'none'; img-src https: data:; style-src 'unsafe-inline'; "
            f"font-src https: data:; frame-ancestors {frame_ancestors}"
        ),
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=data, media_type="text/html; charset=utf-8", headers=headers)
