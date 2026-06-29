"""Search service: Postgres full-text search now, pluggable semantic later."""
from __future__ import annotations

import re
import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.report import (
    Report,
    ReportStatus,
    Tag,
    Technology,
    Visibility,
    report_tags,
    report_technologies,
)
from app.db.models.user import User

# Word tokens only — drops punctuation/underscores so the assembled tsquery is
# always syntactically valid (no need to escape tsquery operators & | ! ( ) :).
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def _prefix_tsquery(query: str):
    """Build a *prefix-matching* tsquery so "kube" matches "kubernetes".

    Each whitespace-separated term becomes a ``<term>:*`` prefix lexeme, and the
    terms are AND-ed together (``kube:* & mesh:*``). This is the database-native
    equivalent of a trie lookup: the existing GIN index on ``search_vector`` is
    walked by lexeme prefix, so no in-memory term tree is needed. Returns a
    SQLAlchemy expression, or ``None`` when the query has no usable word tokens.
    """
    terms = _TOKEN_RE.findall(query.lower())
    if not terms:
        return None
    expr = " & ".join(f"{t}:*" for t in terms)
    return func.to_tsquery("english", expr)


def _eager(stmt):
    return stmt.options(
        selectinload(Report.author),
        selectinload(Report.category),
        selectinload(Report.tags),
        selectinload(Report.technologies),
    )


def full_text_search(
    db: Session,
    query: str | None,
    *,
    category_id: uuid.UUID | None = None,
    tag: str | None = None,
    technology: str | None = None,
    author_id: uuid.UUID | None = None,
    project: str | None = None,
    status: ReportStatus | None = None,
    visibility: Visibility | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[Report, float]], int]:
    """Return (report, rank) tuples + total count.

    When `query` is provided we rank by ts_rank against the maintained
    `search_vector`; otherwise we order by recency.
    """
    filters = []
    if category_id:
        filters.append(Report.category_id == category_id)
    if author_id:
        filters.append(Report.author_id == author_id)
    if project:
        filters.append(Report.project.ilike(f"%{project}%"))
    if status:
        filters.append(Report.status == status)
    if visibility:
        filters.append(Report.visibility == visibility)
    if date_from:
        filters.append(Report.created_at >= date_from)
    if date_to:
        filters.append(Report.created_at <= date_to)

    stmt = select(Report)
    if tag:
        stmt = stmt.join(report_tags).join(Tag).where(Tag.slug == tag)
    if technology:
        stmt = stmt.join(report_technologies).join(Technology).where(Technology.slug == technology)

    ts_query = _prefix_tsquery(query) if query else None
    if ts_query is not None:
        rank = func.ts_rank(Report.search_vector, ts_query).label("rank")
        stmt = stmt.add_columns(rank).where(Report.search_vector.op("@@")(ts_query))
        for f in filters:
            stmt = stmt.where(f)
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = db.scalar(count_stmt) or 0
        stmt = _eager(stmt).order_by(rank.desc()).limit(page_size).offset((page - 1) * page_size)
        rows = db.execute(stmt).all()
        return [(row[0], float(row[1])) for row in rows], total

    # No keyword: filtered recency listing.
    for f in filters:
        stmt = stmt.where(f)
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0
    stmt = _eager(stmt).order_by(Report.created_at.desc()).limit(page_size).offset(
        (page - 1) * page_size
    )
    reports = db.execute(stmt).scalars().all()
    return [(r, 0.0) for r in reports], total


def suggest(db: Session, prefix: str, limit: int = 8) -> list[dict]:
    """Typeahead suggestions for the search box.

    Prefix-matches technology and tag *names* (``ILIKE 'kube%'`` — a B-tree index
    walk, the proper "trie" for autocomplete) and substring-matches report titles
    so "kube" surfaces "kubernetes", the "Kubernetes at Scale" report, etc. — all
    without the user typing the whole word. Returns ordered suggestion dicts.
    """
    prefix = prefix.strip()
    if not prefix:
        return []
    safe = prefix.replace("%", "").replace("_", "")
    starts = f"{safe}%"
    contains = f"%{safe}%"

    out: list[dict] = []
    for name, slug in db.execute(
        select(Technology.name, Technology.slug)
        .where(Technology.name.ilike(starts))
        .order_by(Technology.name)
        .limit(limit)
    ).all():
        out.append({"label": name, "type": "technology", "value": slug})

    for name, slug in db.execute(
        select(Tag.name, Tag.slug)
        .where(Tag.name.ilike(starts))
        .order_by(Tag.name)
        .limit(limit)
    ).all():
        out.append({"label": name, "type": "tag", "value": slug})

    for title, slug in db.execute(
        select(Report.title, Report.slug)
        .where(Report.title.ilike(contains))
        .order_by(Report.created_at.desc())
        .limit(limit)
    ).all():
        out.append({"label": title, "type": "report", "value": slug})

    return out
