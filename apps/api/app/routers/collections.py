"""Collections: user-created folders that group reports."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from slugify import slugify
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user, get_optional_user
from app.db.models.collection import Collection, collection_reports
from app.db.models.report import Report
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.collection import (
    Breadcrumb,
    CollectionCreate,
    CollectionDetail,
    CollectionOut,
    CollectionUpdate,
)
from app.schemas.report import ReportSummary

router = APIRouter(prefix="/collections", tags=["collections"])

_REPORT_EAGER = (
    selectinload(Report.author), selectinload(Report.category),
    selectinload(Report.tags), selectinload(Report.technologies),
)


def _count(db: Session, collection_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count()).select_from(collection_reports)
        .where(collection_reports.c.collection_id == collection_id)
    ) or 0


def _subfolder_count(db: Session, collection_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count()).select_from(Collection)
        .where(Collection.parent_id == collection_id)
    ) or 0


def _to_out(db: Session, c: Collection) -> CollectionOut:
    out = CollectionOut.model_validate(c)
    out.report_count = _count(db, c.id)
    out.subfolder_count = _subfolder_count(db, c.id)
    return out


def _breadcrumbs(db: Session, c: Collection) -> list[Breadcrumb]:
    """Walk up parents to build a path (root → … → current)."""
    chain: list[Breadcrumb] = []
    node: Collection | None = c
    seen: set[uuid.UUID] = set()
    while node is not None and node.id not in seen:
        seen.add(node.id)
        chain.append(Breadcrumb(id=node.id, name=node.name, slug=node.slug))
        node = db.get(Collection, node.parent_id) if node.parent_id else None
    return list(reversed(chain))


def _is_descendant(db: Session, candidate_id: uuid.UUID, of_id: uuid.UUID) -> bool:
    """True if candidate is `of` or a descendant of it (used to block cycles)."""
    node = db.get(Collection, candidate_id)
    seen: set[uuid.UUID] = set()
    while node is not None and node.id not in seen:
        if node.id == of_id:
            return True
        seen.add(node.id)
        node = db.get(Collection, node.parent_id) if node.parent_id else None
    return False


@router.get("", response_model=list[CollectionOut])
def list_collections(
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
    parent_id: uuid.UUID | None = None,
    top_level: bool = True,
):
    """Collections visible to the user. By default only top-level folders are
    returned (so the dashboard shows roots); pass `parent_id` to list children,
    or `top_level=false` to list everything (flat)."""
    stmt = select(Collection).options(selectinload(Collection.owner))
    if user:
        stmt = stmt.where(or_(Collection.owner_id == user.id, Collection.is_public.is_(True)))
    else:
        stmt = stmt.where(Collection.is_public.is_(True))
    if parent_id is not None:
        stmt = stmt.where(Collection.parent_id == parent_id)
    elif top_level:
        stmt = stmt.where(Collection.parent_id.is_(None))
    rows = db.scalars(stmt.order_by(Collection.created_at.desc())).all()
    return [_to_out(db, c) for c in rows]


@router.post("", response_model=CollectionOut, status_code=201)
def create_collection(
    payload: CollectionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if payload.parent_id is not None:
        parent = db.get(Collection, payload.parent_id)
        if not parent:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Parent collection not found")
        if parent.owner_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your parent collection")
    base = slugify(payload.name) or "collection"
    slug, i = base, 2
    while db.scalar(select(Collection.id).where(Collection.slug == slug)) is not None:
        slug, i = f"{base}-{i}", i + 1
    c = Collection(
        owner_id=user.id, name=payload.name, slug=slug,
        description=payload.description, is_public=payload.is_public,
        parent_id=payload.parent_id,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _to_out(db, c)


def _get(db: Session, id_or_slug: str) -> Collection:
    stmt = select(Collection).options(
        selectinload(Collection.owner),
        selectinload(Collection.reports).options(*_REPORT_EAGER),
        selectinload(Collection.children).selectinload(Collection.owner),
    )
    try:
        stmt = stmt.where(Collection.id == uuid.UUID(id_or_slug))
    except ValueError:
        stmt = stmt.where(Collection.slug == id_or_slug)
    c = db.scalar(stmt)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")
    return c


@router.get("/{id_or_slug}", response_model=CollectionDetail)
def get_collection(
    id_or_slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)
):
    c = _get(db, id_or_slug)
    if not c.is_public and (not user or user.id != c.owner_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This collection is private")
    detail = CollectionDetail.model_validate(c)
    detail.report_count = len(c.reports)
    detail.subfolder_count = len(c.children)
    detail.reports = [ReportSummary.model_validate(r) for r in c.reports]
    detail.children = [_to_out(db, child) for child in c.children]
    detail.breadcrumbs = _breadcrumbs(db, c)
    return detail


@router.patch("/{id_or_slug}", response_model=CollectionOut)
def update_collection(
    id_or_slug: str, payload: CollectionUpdate,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    c = _get(db, id_or_slug)
    if c.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your collection")
    data = payload.model_dump(exclude_unset=True)
    if "parent_id" in data and data["parent_id"] is not None:
        new_parent = data["parent_id"]
        if new_parent == c.id or _is_descendant(db, new_parent, c.id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot nest a folder inside itself")
    for k, v in data.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return _to_out(db, c)


@router.delete("/{id_or_slug}", status_code=204)
def delete_collection(
    id_or_slug: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    c = _get(db, id_or_slug)
    if c.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your collection")
    db.delete(c)
    db.commit()


@router.put("/{id_or_slug}/reports/{report_id}", status_code=204)
def add_report(
    id_or_slug: str, report_id: uuid.UUID,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    c = _get(db, id_or_slug)
    if c.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your collection")
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if report not in c.reports:
        c.reports.append(report)
        db.commit()


@router.delete("/{id_or_slug}/reports/{report_id}", status_code=204)
def remove_report(
    id_or_slug: str, report_id: uuid.UUID,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    c = _get(db, id_or_slug)
    if c.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your collection")
    report = db.get(Report, report_id)
    if report and report in c.reports:
        c.reports.remove(report)
        db.commit()
