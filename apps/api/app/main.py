"""Kelp Nexus API entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.routers import (
    admin,
    auth,
    collections,
    comments,
    dashboard,
    favorites,
    related,
    reports,
    search,
    taxonomy,
    users,
)

app = FastAPI(
    title="Kelp Nexus API",
    version="0.1.0",
    description="Internal Engineering Knowledge Portal API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Required by Authlib for the OIDC state during the Azure AD redirect flow.
app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "ai_enabled": settings.enable_ai}


_v1 = settings.api_v1_prefix
for r in (
    auth.router, reports.router, search.router, comments.router, favorites.router,
    taxonomy.router, users.router, dashboard.router, related.router, admin.router,
    collections.router,
):
    app.include_router(r, prefix=_v1)
