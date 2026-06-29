"""Admin panel: user/role management + audit log."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.models.audit import AuditLog
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.user import RoleUpdate, UserPublic

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserPublic])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_role(Role.admin))):
    return db.scalars(select(User).order_by(User.created_at.desc())).all()


@router.patch("/users/{user_id}/role", response_model=UserPublic)
def set_role(
    user_id: uuid.UUID,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(Role.admin)),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.role = payload.role
    db.add(AuditLog(
        actor_id=actor.id, action="set_role", entity_type="user",
        entity_id=str(user_id), detail=f"role={payload.role.value}",
    ))
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/deactivate", response_model=UserPublic)
def deactivate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(Role.admin)),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.is_active = False
    db.add(AuditLog(actor_id=actor.id, action="deactivate", entity_type="user",
                    entity_id=str(user_id)))
    db.commit()
    db.refresh(user)
    return user


class AuditEntry(BaseModel):
    id: uuid.UUID
    action: str
    entity_type: str
    entity_id: str | None
    detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/audit-log", response_model=list[AuditEntry])
def audit_log(db: Session = Depends(get_db), _: User = Depends(require_role(Role.admin))):
    return db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)).all()
