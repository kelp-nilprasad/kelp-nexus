"""MSAL (Microsoft Entra ID) client + auth-code-flow helpers.

Supports both a confidential client (when MSAL_CLIENT_SECRET is set) and a public
client (PKCE only). The flow is bridged to our own DB users + session JWT in the
auth router, so the rest of the app stays provider-agnostic.
"""
from __future__ import annotations

from functools import lru_cache

import msal

from app.core.config import settings


@lru_cache
def get_msal_app() -> msal.ClientApplication | None:
    if not settings.msal_configured:
        return None
    if settings.msal_client_secret:
        return msal.ConfidentialClientApplication(
            client_id=settings.msal_client_id,
            client_credential=settings.msal_client_secret,
            authority=settings.msal_authority,
        )
    return msal.PublicClientApplication(
        client_id=settings.msal_client_id,
        authority=settings.msal_authority,
    )


def build_auth_code_flow() -> dict:
    """Start an auth-code flow (with PKCE); the dict must be stashed in the session."""
    app = get_msal_app()
    assert app is not None
    return app.initiate_auth_code_flow(
        scopes=settings.msal_scopes,
        redirect_uri=settings.msal_redirect_uri,
    )


def acquire_token_by_flow(flow: dict, auth_response: dict) -> dict:
    app = get_msal_app()
    assert app is not None
    return app.acquire_token_by_auth_code_flow(flow, auth_response)
