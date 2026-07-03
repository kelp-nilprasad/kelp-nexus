"""MSAL (Microsoft Entra ID) client + auth-code-flow helpers.

Supports both a confidential client (when MSAL_CLIENT_SECRET is set) and a public
client (PKCE only). The flow is bridged to our own DB users + session JWT in the
auth router, so the rest of the app stays provider-agnostic.

SharePoint storage uses an APP-ONLY Microsoft Graph token (client credentials via
`acquire_app_graph_token`) — the app acts as its own identity, so any signed-in
user can read/write the document library without a per-user Graph token.
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


_GRAPH_DEFAULT_SCOPE = ["https://graph.microsoft.com/.default"]


@lru_cache
def _app_only_client() -> "msal.ConfidentialClientApplication | None":
    """Confidential client used for app-only (client-credentials) Graph tokens."""
    if not settings.sharepoint_configured:
        return None
    return msal.ConfidentialClientApplication(
        client_id=settings.msal_client_id,
        authority=settings.msal_authority,
        client_credential=settings.msal_client_secret,
    )


def acquire_app_graph_token() -> str | None:
    """App-only Microsoft Graph access token (client credentials).

    MSAL caches the token in-memory and transparently refreshes it before expiry,
    so this is cheap to call per request. Returns None if SharePoint/MSAL isn't
    configured or the token could not be acquired.
    """
    app = _app_only_client()
    if app is None:
        return None
    result = app.acquire_token_for_client(scopes=_GRAPH_DEFAULT_SCOPE)
    if not result or "access_token" not in result:
        return None
    return result["access_token"]
