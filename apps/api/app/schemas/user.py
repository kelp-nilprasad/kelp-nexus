"""User / auth Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.db.models.user import Role


class UserBase(BaseModel):
    email: EmailStr
    name: str
    team: str | None = None
    department: str | None = None
    title: str | None = None
    bio: str | None = None
    avatar_url: str | None = None


class UserPublic(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    role: Role
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = None
    team: str | None = None
    department: str | None = None
    title: str | None = None
    bio: str | None = None
    avatar_url: str | None = None


class RoleUpdate(BaseModel):
    role: Role


class DevLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
