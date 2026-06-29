"""Azure AD / Entra ID OIDC integration via Authlib.

Only active when azure_tenant_id + azure_client_id are configured. The auth
router exposes /auth/login (redirect) and /auth/callback (code exchange). On
success we upsert a local User keyed by the token's `oid` and issue our own
session JWT — so the rest of the app is provider-agnostic.
"""
from __future__ import annotations

from functools import lru_cache

from authlib.integrations.starlette_client import OAuth

from app.core.config import settings


def azure_configured() -> bool:
    return bool(settings.azure_tenant_id and settings.azure_client_id)


@lru_cache
def get_oauth() -> OAuth | None:
    if not azure_configured():
        return None
    oauth = OAuth()
    oauth.register(
        name="azure",
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
        server_metadata_url=(
            f"https://login.microsoftonline.com/{settings.azure_tenant_id}/v2.0/"
            ".well-known/openid-configuration"
        ),
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth
