"""Categories, tags, technologies — listing + admin management."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.models.report import Category, Tag, Technology, report_technologies
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.report import CategoryOut, TaxonomyItem

router = APIRouter(tags=["taxonomy"])


class CategoryCreate(BaseModel):
    name: str
    description: str | None = None
    parent_id: uuid.UUID | None = None


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.name)).all()


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.editor)),
):
    cat = Category(
        name=payload.name, slug=slugify(payload.name),
        description=payload.description, parent_id=payload.parent_id,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.get("/tags", response_model=list[TaxonomyItem])
def list_tags(db: Session = Depends(get_db)):
    return db.scalars(select(Tag).order_by(Tag.name)).all()


class TechnologyCount(BaseModel):
    name: str
    slug: str
    count: int


@router.get("/technologies", response_model=list[TaxonomyItem])
def list_technologies(db: Session = Depends(get_db)):
    return db.scalars(select(Technology).order_by(Technology.name)).all()


@router.get("/technologies/cloud", response_model=list[TechnologyCount])
def technology_cloud(db: Session = Depends(get_db)):
    """Technology usage counts for the dashboard tech cloud."""
    rows = db.execute(
        select(Technology.name, Technology.slug, func.count(report_technologies.c.report_id))
        .outerjoin(report_technologies, Technology.id == report_technologies.c.technology_id)
        .group_by(Technology.id)
        .order_by(func.count(report_technologies.c.report_id).desc())
    ).all()
    return [TechnologyCount(name=n, slug=s, count=c) for n, s, c in rows]
