"""MSAL (Microsoft Entra ID) client + auth-code-flow helpers.

Supports both a confidential client (when MSAL_CLIENT_SECRET is set) and a public
client (PKCE only). The flow is bridged to our own DB users + session JWT in the
auth router, so the rest of the app stays provider-agnostic.

When the SharePoint storage backend is active we also request delegated Microsoft
Graph scopes at sign-in and persist the per-user MSAL token cache, so later
requests can acquire a Graph token silently (via the stored refresh token) to
read/write the SharePoint document library on the user's behalf.
"""
from __future__ import annotations

from functools import lru_cache

import msal

from app.core.config import settings


def _build_app(token_cache: "msal.SerializableTokenCache | None" = None) -> msal.ClientApplication | None:
    if not settings.msal_configured:
        return None
    common = dict(
        client_id=settings.msal_client_id,
        authority=settings.msal_authority,
        token_cache=token_cache,
    )
    if settings.msal_client_secret:
        return msal.ConfidentialClientApplication(
            client_credential=settings.msal_client_secret, **common
        )
    return msal.PublicClientApplication(**common)


@lru_cache
def get_msal_app() -> msal.ClientApplication | None:
    # Cacheless app used only to build the login redirect / configured check.
    return _build_app()


def build_auth_code_flow() -> dict:
    """Start an auth-code flow (with PKCE); the dict must be stashed in the session."""
    app = get_msal_app()
    assert app is not None
    return app.initiate_auth_code_flow(
        scopes=settings.login_scopes,
        redirect_uri=settings.msal_redirect_uri,
    )


def acquire_token_by_flow(flow: dict, auth_response: dict) -> tuple[dict, str | None]:
    """Redeem the auth code. Returns (result, serialized_token_cache_or_None).

    The serialized cache holds the delegated Graph refresh token and should be
    persisted on the user so we can acquire Graph tokens silently later.
    """
    cache = msal.SerializableTokenCache()
    app = _build_app(cache)
    assert app is not None
    result = app.acquire_token_by_auth_code_flow(flow, auth_response)
    serialized = cache.serialize() if cache.has_state_changed else None
    return result, serialized


def acquire_graph_token(serialized_cache: str | None) -> tuple[str | None, str | None]:
    """Silently get a delegated Graph access token from a stored MSAL cache.

    Returns (access_token_or_None, refreshed_serialized_cache_or_None). The cache
    should be re-persisted when a refreshed copy is returned.
    """
    if not serialized_cache:
        return None, None
    cache = msal.SerializableTokenCache()
    cache.deserialize(serialized_cache)
    app = _build_app(cache)
    if app is None:
        return None, None
    accounts = app.get_accounts()
    if not accounts:
        return None, None
    result = app.acquire_token_silent(settings.graph_scopes, account=accounts[0])
    refreshed = cache.serialize() if cache.has_state_changed else None
    if not result or "access_token" not in result:
        return None, refreshed
    return result["access_token"], refreshed
