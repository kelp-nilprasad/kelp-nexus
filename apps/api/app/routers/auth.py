"""Authentication: Microsoft Entra ID (MSAL SSO) + local dev-login fallback.

The Microsoft handshake is bridged to our own model: on success we upsert a local
User keyed by the token's `oid` and issue our session JWT cookie, so RBAC,
authorship, and comments work the same regardless of how the user signed in.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.msal_client import acquire_token_by_flow, build_auth_code_flow, get_msal_app
from app.core.security import create_access_token, verify_password
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.user import DevLoginRequest, TokenResponse, UserPublic

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE = "access_token"
_FLOW_KEY = "msal_auth_flow"


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.environment != "development",
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


def _upsert_user(db: Session, *, oid: str, email: str, name: str) -> User:
    user = db.scalar(select(User).where(User.azure_oid == oid))
    if user is None and email:
        user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(azure_oid=oid, email=email, name=name or email, role=Role.author)
        db.add(user)
    else:
        user.azure_oid = oid
        if name:
            user.name = name
    db.commit()
    db.refresh(user)
    return user


@router.post("/dev-login", response_model=TokenResponse)
def dev_login(payload: DevLoginRequest, response: Response, db: Session = Depends(get_db)):
    """Local email/password login. Disabled unless DEV_LOGIN=true."""
    if not settings.dev_login:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dev login disabled")
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not user.hashed_password or not verify_password(
        payload.password, user.hashed_password
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token = create_access_token(str(user.id), user.role.value)
    _set_cookie(response, token)
    return TokenResponse(access_token=token, user=UserPublic.model_validate(user))


@router.get("/login")
def login(request: Request):
    """Begin the Microsoft Entra sign-in (redirect to login.microsoftonline.com)."""
    if not get_msal_app():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Microsoft sign-in not configured")
    flow = build_auth_code_flow()
    request.session[_FLOW_KEY] = flow
    return RedirectResponse(flow["auth_uri"])


@router.get("/callback")
def callback(request: Request, db: Session = Depends(get_db)):
    """Entra redirect target: validate the code, upsert the user, set session cookie."""
    if not get_msal_app():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Microsoft sign-in not configured")
    flow = request.session.pop(_FLOW_KEY, None)
    if not flow:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Auth flow expired; please retry")

    result, token_cache = acquire_token_by_flow(flow, dict(request.query_params))
    if "error" in result:
        logger.warning("MSAL error: %s — %s", result.get("error"), result.get("error_description"))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, result.get("error_description", "Sign-in failed"))

    claims = result.get("id_token_claims", {})
    oid = claims.get("oid") or claims.get("sub")
    email = claims.get("preferred_username") or claims.get("email") or ""
    name = claims.get("name") or email
    if not oid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incomplete profile from Microsoft")

    user = _upsert_user(db, oid=oid, email=email, name=name)
    # Persist the delegated Graph token cache for later SharePoint access.
    if token_cache:
        user.msal_token_cache = token_cache
        db.commit()
    token = create_access_token(str(user.id), user.role.value)
    redirect = RedirectResponse(url=f"{settings.web_base_url}/dashboard")
    redirect.set_cookie(
        COOKIE, token, httponly=True, samesite="lax",
        secure=settings.environment != "development",
        max_age=settings.jwt_expire_minutes * 60, path="/",
    )
    return redirect


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/config")
def auth_config():
    """Lets the frontend know which login methods are available."""
    return {"microsoft": settings.msal_configured, "dev_login": settings.dev_login}
