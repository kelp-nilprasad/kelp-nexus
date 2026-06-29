"""Helpers to upsert tags/technologies and generate unique slugs."""
from __future__ import annotations

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.report import Report, Tag, Technology


def unique_report_slug(db: Session, title: str) -> str:
    base = slugify(title) or "report"
    slug = base
    i = 2
    while db.scalar(select(Report.id).where(Report.slug == slug)) is not None:
        slug = f"{base}-{i}"
        i += 1
    return slug


def upsert_tags(db: Session, names: list[str]) -> list[Tag]:
    out: list[Tag] = []
    for name in {n.strip() for n in names if n.strip()}:
        slug = slugify(name)
        tag = db.scalar(select(Tag).where(Tag.slug == slug))
        if tag is None:
            tag = Tag(name=name, slug=slug)
            db.add(tag)
            db.flush()
        out.append(tag)
    return out


def upsert_technologies(db: Session, names: list[str]) -> list[Technology]:
    out: list[Technology] = []
    for name in {n.strip() for n in names if n.strip()}:
        slug = slugify(name)
        tech = db.scalar(select(Technology).where(Technology.slug == slug))
        if tech is None:
            tech = Technology(name=name, slug=slug)
            db.add(tech)
            db.flush()
        out.append(tech)
    return out
