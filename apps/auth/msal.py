"""MSAL authentication routes and helpers."""

from __future__ import annotations

import logging
from typing import Annotated
from urllib.parse import quote, urlsplit

import msal
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.settings import get_settings

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)

# Dedicated logger for 307 redirects so each redirect's reason is visible
# in production logs (root level is ERROR). Mirrors app.diagnostics.
redirect_logger = logging.getLogger("app.redirects")
redirect_logger.setLevel(logging.INFO)


def _compact_auth_flow(flow: dict) -> dict:
    """
    Keep only fields needed for token exchange/state validation.
    Avoid storing `auth_uri` in cookie-based session to keep headers small.
    """
    keep_keys = (
        "state",
        "redirect_uri",
        "scope",
        "code_verifier",
        "nonce",
        "claims_challenge",
    )
    return {k: flow.get(k) for k in keep_keys if k in flow}


def _authority() -> str:
    settings = get_settings()
    return f"https://login.microsoftonline.com/{settings.msal_tenant_id}"


def _redirect_uri(request: Request) -> str:
    settings = get_settings()
    if settings.msal_redirect_uri:
        return settings.msal_redirect_uri.strip()

    return urlsplit(str(request.url_for("auth_callback"))).path


def _normalize_safe_redirect_target(request: Request, target: str | None) -> str:
    """
    Allow only relative paths or same-origin absolute URLs.
    Any invalid target falls back to root.
    """
    if not target:
        return "/"
    raw = str(target).strip()
    if not raw:
        return "/"

    parsed = urlsplit(raw)
    # Relative path target
    if not parsed.scheme and not parsed.netloc:
        if not raw.startswith("/"):
            return "/"
        if raw.startswith("//"):
            return "/"
        return raw

    # Same-origin absolute URL target
    current_origin = urlsplit(str(request.base_url))
    if parsed.scheme == current_origin.scheme and parsed.netloc == current_origin.netloc:
        path = parsed.path or "/"
        query = f"?{parsed.query}" if parsed.query else ""
        fragment = f"#{parsed.fragment}" if parsed.fragment else ""
        return f"{path}{query}{fragment}"
    return "/"


def _scopes() -> list[str]:
    # MSAL adds OIDC reserved scopes automatically. Request a standard
    # delegated scope so auth code flow is valid.
    return ["User.Read"]


def _msal_application() -> msal.ClientApplication:
    """
    Web redirect URIs in Entra are usually confidential clients (secret required).
    Use MSAL_CLIENT_SECRET for that case. If unset, use a public client (PKCE);
    then Entra must have allowPublicClient enabled for the same registration.
    """
    settings = get_settings()
    authority = _authority()
    client_id = settings.msal_client_id
    secret = (settings.msal_client_secret or "").strip()
    if secret:
        return msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=secret,
            authority=authority,
        )
    return msal.PublicClientApplication(
        client_id=client_id,
        authority=authority,
    )


def _user_from_auth_result(result: dict[str, object]) -> dict[str, str | None]:
    claims_raw = result.get("id_token_claims")
    claims = claims_raw if isinstance(claims_raw, dict) else {}

    account_raw = result.get("account")
    account = account_raw if isinstance(account_raw, dict) else {}

    preferred_username = (
        claims.get("preferred_username")
        or claims.get("upn")
        or claims.get("email")
        or account.get("username")
    )
    name = claims.get("name") or account.get("name")
    oid = claims.get("oid") or claims.get("sub")
    tid = claims.get("tid")

    return {
        "oid": str(oid) if oid else None,
        "name": str(name) if name else None,
        "preferred_username": str(preferred_username) if preferred_username else None,
        "tid": str(tid) if tid else None,
    }


def _is_valid_authenticated_user(user: dict[str, str | None]) -> bool:
    oid = str(user.get("oid") or "").strip()
    username = str(user.get("preferred_username") or "").strip()
    tid = str(user.get("tid") or "").strip()
    return bool((oid or username) and tid)


async def _auth_response_payload(request: Request) -> dict[str, str]:
    if request.method == "POST":
        form = await request.form()
        return {str(key): str(value) for key, value in form.items()}
    return {str(key): str(value) for key, value in request.query_params.items()}


@router.get("/auth/login")
async def auth_login(request: Request, next_url: Annotated[str | None, Query(alias="next")] = None):
    safe_next = _normalize_safe_redirect_target(request, next_url)

    # Use MSAL-managed auth code flow so state/PKCE handling stays
    # compatible across MSAL versions.
    flow = _msal_application().initiate_auth_code_flow(
        scopes=_scopes(),
        redirect_uri=_redirect_uri(request),
        prompt="select_account",
    )
    logger.info("Initiated MSAL auth code flow: state=%s", flow.get("state"))
    compact_flow = _compact_auth_flow(flow)
    state = str(compact_flow.get("state") or "").strip()
    if state:
        flows = request.session.get("msal_auth_flows")
        if not isinstance(flows, dict):
            flows = {}
        # Session is cookie-backed. Keep only a tiny rolling window.
        while len(flows) >= 5:
            oldest_state = next(iter(flows))
            flows.pop(oldest_state, None)
        flows[state] = compact_flow
        request.session["msal_auth_flows"] = flows
    else:
        # Backward-compatible fallback if MSAL does not return state.
        request.session["msal_auth_flow"] = compact_flow
    if safe_next and safe_next != "/":
        request.session["post_auth_redirect"] = safe_next
    auth_url = str(flow.get("auth_uri") or "")
    if not auth_url:
        return JSONResponse(
            status_code=500, content={"detail": "Failed to initialize Microsoft login"}
        )
    redirect_logger.info(
        "[redirect 307] reason=auth_login_to_microsoft next=%s redirect_uri=%s",
        safe_next,
        _redirect_uri(request),
    )
    return RedirectResponse(auth_url, status_code=307)


async def _auth_callback_impl(request: Request):
    auth_response = await _auth_response_payload(request)
    state = str(auth_response.get("state") or "").strip()
    logger.info("Received auth callback: state=%s, has_code=%s", state, "code" in auth_response)
    flow = None
    if state:
        flows = request.session.get("msal_auth_flows")
        if isinstance(flows, dict):
            flow = flows.pop(state, None)
            request.session["msal_auth_flows"] = flows
    if not isinstance(flow, dict):
        # Backward-compatible fallback for already-issued sessions.
        flow = request.session.get("msal_auth_flow")
        request.session.pop("msal_auth_flow", None)
    if not isinstance(flow, dict):
        return JSONResponse(status_code=400, content={"detail": "Missing auth flow in session"})
    try:
        logger.info("Acquiring token by auth code flow for state=%s", state)
        result = _msal_application().acquire_token_by_auth_code_flow(flow, auth_response)
        logger.info("MSAL token acquisition result: success=%s", "access_token" in result)
    except Exception as exc:
        logger.exception("MSAL token exchange exception: %s", exc)
        return JSONResponse(status_code=400, content={"detail": "Invalid Microsoft login response"})
    if "error" in result:
        err = result.get("error")
        sub = result.get("suberror")
        desc = result.get("error_description")
        # Use ERROR so this appears when APP_LOG_LEVEL is ERROR (production).
        logger.error(
            "MSAL token exchange failed: error=%s suberror=%s description=%s",
            err,
            sub,
            desc,
        )
        payload: dict = {
            "detail": "Microsoft login failed",
            "microsoft_error": err,
        }
        if sub:
            payload["microsoft_suberror"] = sub
        if desc:
            payload["microsoft_error_description"] = desc
        if isinstance(desc, str) and "AADSTS7000218" in desc:
            payload["hint"] = (
                "This app runs without MSAL_CLIENT_SECRET (public client + PKCE). "
                "In Entra: App registration -> Authentication -> enable "
                '"Allow public client flows", or set manifest allowPublicClient to true. '
                "Otherwise add a client secret in Entra and set MSAL_CLIENT_SECRET."
            )
        return JSONResponse(status_code=401, content=payload)

    user = _user_from_auth_result(result)
    logger.info("Extracted user from auth result: %s", user)
    if not _is_valid_authenticated_user(user):
        logger.error("MSAL callback produced non-attributable user payload: %s", user)
        return JSONResponse(status_code=401, content={"detail": "Invalid Microsoft login identity"})
    request.session["user"] = user
    logger.info("User session established for %s", user.get("preferred_username"))
    request.session.pop("msal_auth_flow", None)

    next_url = _normalize_safe_redirect_target(
        request, str(request.session.pop("post_auth_redirect", "/") or "/")
    )
    redirect_logger.info(
        "[redirect 307] reason=auth_callback_complete user=%s -> %s",
        user.get("preferred_username") or user.get("oid"),
        next_url,
    )
    return RedirectResponse(next_url, status_code=307)


@router.api_route("/auth/callback", methods=["GET", "POST"], name="auth_callback")
async def auth_callback(request: Request):
    return await _auth_callback_impl(request)


@router.api_route("/auth/callback/", methods=["GET", "POST"])
async def auth_callback_trailing_slash(request: Request):
    return await _auth_callback_impl(request)


@router.post("/auth/logout")
async def auth_logout(request: Request):
    request.session.clear()
    logout_url = (
        f"{_authority()}/oauth2/v2.0/logout"
        f"?post_logout_redirect_uri={quote(str(request.base_url), safe=':/')}"
    )
    redirect_logger.info(
        "[redirect 307] reason=auth_logout_to_microsoft post_logout=%s",
        str(request.base_url),
    )
    return RedirectResponse(logout_url, status_code=307)


@router.get("/api/auth/me")
async def auth_me(request: Request):
    user = getattr(request.state, "user", None) or request.session.get("user")
    if not user:
        return JSONResponse(status_code=401, content={"detail": "Authentication required"})
    return {"user": user}
