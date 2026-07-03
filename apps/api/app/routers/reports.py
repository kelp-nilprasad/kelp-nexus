"""Report CRUD, HTML/PDF upload, versioning, and rendering."""
from __future__ import annotations

import logging
import uuid

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.deps import get_current_user, get_optional_user, require_role
from app.core.msal_client import acquire_graph_token
from app.services import sharepoint
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


def _classify_media(content_type: str | None, filename: str | None) -> str:
    """Map an upload to how the frontend should view it: html | pdf | video | other."""
    ct = (content_type or "").lower()
    name = (filename or "").lower()
    if "html" in ct or name.endswith((".html", ".htm")):
        return "html"
    if "pdf" in ct or name.endswith(".pdf"):
        return "pdf"
    if ct.startswith("video/") or name.endswith((".mp4", ".webm", ".mov", ".m4v", ".ogv")):
        return "video"
    return "other"


def _version_out(v: ReportVersion) -> ReportVersionOut:
    kind = v.media_kind or ("html" if v.html_blob_path else "pdf" if v.pdf_blob_path else None)
    return ReportVersionOut(
        id=v.id, version=v.version, changelog=v.changelog, created_at=v.created_at,
        has_html=bool(v.html_blob_path) or kind == "html",
        has_pdf=bool(v.pdf_blob_path) or kind == "pdf",
        media_kind=kind, content_type=v.content_type, asset_name=v.asset_name,
    )


def _detail(report: Report) -> ReportDetail:
    detail = ReportDetail.model_validate(report)
    detail.versions = [_version_out(v) for v in report.versions]
    return detail


def _graph_token(user: User | None, db: Session) -> str:
    """Delegated Graph token for the current user; refreshes + re-persists the cache."""
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in with Microsoft to access SharePoint")
    token, refreshed = acquire_graph_token(user.msal_token_cache)
    if refreshed:
        user.msal_token_cache = refreshed
        db.commit()
    if not token:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "SharePoint access requires signing in with Microsoft (no valid token).",
        )
    return token


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


_EXT_BY_KIND = {"html": "html", "pdf": "pdf"}
_VIDEO_EXTS = {"video/mp4": "mp4", "video/webm": "webm", "video/quicktime": "mov", "video/ogg": "ogv"}


@router.post("/{slug_or_id}/versions", response_model=ReportVersionOut)
async def upload_version(
    slug_or_id: str,
    file: UploadFile | None = File(None),
    # Legacy field names kept so older clients still work.
    html: UploadFile | None = File(None),
    pdf: UploadFile | None = File(None),
    changelog: str | None = Form(None),
    auto_summarize: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a file (HTML, PDF, or video) as a new version. HTML is sanitized on ingest."""
    report = _get_or_404(db, slug_or_id)
    if report.author_id != user.id and user.role not in (Role.admin, Role.editor):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot add a version")
    upload = file or html or pdf
    if not upload:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide a file to upload")

    kind = _classify_media(upload.content_type, upload.filename)
    raw = await upload.read()
    new_version = report.current_version + 1 if report.versions else 1
    extracted = None

    if kind == "html":
        clean = sanitize_html(raw.decode("utf-8", errors="replace"))
        extracted = extract_text(clean)
        report.content_text = extracted  # feeds the FTS trigger
        data, content_type, ext = clean.encode("utf-8"), "text/html; charset=utf-8", "html"
    elif kind == "pdf":
        data, content_type, ext = raw, "application/pdf", "pdf"
    elif kind == "video":
        content_type = upload.content_type or "video/mp4"
        data, ext = raw, _VIDEO_EXTS.get(content_type, "mp4")
    else:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Unsupported file type. Upload an HTML, PDF, or video file.",
        )

    rel_path = f"reports/{report.id}/v{new_version}/asset.{ext}"
    if settings.use_sharepoint:
        asset_path = sharepoint.upload(_graph_token(user, db), rel_path, data, content_type)
    else:
        asset_path = get_storage().upload(rel_path, data, content_type)
    if kind == "html" and auto_summarize and extracted:
        summary = generate_summary(extracted)
        if summary:
            report.summary = summary
        ai_tags = generate_tags(extracted)
        if ai_tags:
            report.tags = upsert_tags(db, [t.name for t in report.tags] + ai_tags)

    version = ReportVersion(
        report_id=report.id, version=new_version,
        # Mirror to legacy columns so existing render/queries keep working.
        html_blob_path=asset_path if kind == "html" else None,
        pdf_blob_path=asset_path if kind == "pdf" else None,
        asset_path=asset_path, asset_name=upload.filename,
        content_type=content_type, media_kind=kind,
        extracted_text=extracted, changelog=changelog, created_by=user.id,
    )
    db.add(version)
    report.current_version = new_version
    db.commit()
    db.refresh(version)
    return _version_out(version)


def _parse_range(range_header: str | None, size: int) -> tuple[int, int] | None:
    """Parse a single `bytes=start-end` range against `size`; None if absent/invalid."""
    if not range_header or not range_header.startswith("bytes="):
        return None
    try:
        start_s, _, end_s = range_header[len("bytes="):].partition("-")
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else size - 1
    except ValueError:
        return None
    end = min(end, size - 1)
    if start > end or start < 0:
        return None
    return start, end


@router.get("/{slug_or_id}/render", response_class=Response)
def render_html(
    request: Request,
    slug_or_id: str,
    version: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """Serve a report version's asset for viewing (HTML/PDF into a sandboxed iframe,
    video into a <video> player with HTTP range support)."""
    report = _get_or_404(db, slug_or_id)
    target = None
    for v in sorted(report.versions, key=lambda x: x.version, reverse=True):
        if (version is None or v.version == version) and (v.asset_path or v.html_blob_path):
            target = v
            break
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No viewable content for this report/version")

    path = target.asset_path or target.html_blob_path
    kind = target.media_kind or ("html" if target.html_blob_path else "pdf")

    # SharePoint video: redirect to a short-lived pre-authed URL so the browser
    # streams (with range) straight from SharePoint instead of via our process.
    if kind == "video" and settings.use_sharepoint:
        url = sharepoint.download_url(_graph_token(user, db), path)
        if not url:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Video is unavailable")
        return RedirectResponse(url)

    try:
        if settings.use_sharepoint:
            data = sharepoint.download(_graph_token(user, db), path)
        else:
            data = get_storage().download(path)
    except HTTPException:
        raise
    except Exception as exc:  # blob missing / storage unreachable
        # Surface a clear error instead of an opaque 500 rendered inside the iframe.
        logger.exception(
            "Failed to load report asset %s (report %s): %s", path, report.id, exc,
        )
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Report content is unavailable (could not read it from storage).",
        ) from exc

    # frame-ancestors must list the web origin(s) or the browser blocks the iframe
    # in production (localhost only works in dev).
    frame_ancestors = " ".join(settings.cors_origins) or "'self'"

    if kind == "video":
        content_type = target.content_type or "video/mp4"
        rng = _parse_range(request.headers.get("range"), len(data))
        common = {"Accept-Ranges": "bytes", "Cache-Control": "private, max-age=3600"}
        if rng:
            start, end = rng
            chunk = data[start:end + 1]
            return Response(
                content=chunk, status_code=status.HTTP_206_PARTIAL_CONTENT,
                media_type=content_type,
                headers={**common, "Content-Range": f"bytes {start}-{end}/{len(data)}",
                         "Content-Length": str(len(chunk))},
            )
        return Response(content=data, media_type=content_type, headers=common)

    if kind == "pdf":
        headers = {
            "Content-Security-Policy": f"frame-ancestors {frame_ancestors}",
            "Content-Disposition": "inline",
        }
        return Response(content=data, media_type="application/pdf", headers=headers)

    # html (default): locked-down CSP for the sandboxed iframe.
    headers = {
        "Content-Security-Policy": (
            "default-src 'none'; img-src https: data:; style-src 'unsafe-inline'; "
            f"font-src https: data:; frame-ancestors {frame_ancestors}"
        ),
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=data, media_type="text/html; charset=utf-8", headers=headers)
