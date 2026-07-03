"""SharePoint storage backend via Microsoft Graph (app-only token).

Files are stored in a SharePoint site's document library (drive). Callers pass an
app-only Graph access token (the app's own identity, see
`core.msal_client.acquire_app_graph_token`). The DB stores the Graph **drive item
id** as the asset path.

Resolution of the site id and drive id is cached process-wide (they are stable).
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GRAPH = "https://graph.microsoft.com/v1.0"
_TIMEOUT = httpx.Timeout(60.0, connect=15.0)
# Graph resumable upload requires chunks that are multiples of 320 KiB.
_CHUNK = 8 * 320 * 1024  # ~2.6 MB
_SIMPLE_MAX = 4 * 1024 * 1024  # <=4 MB -> simple PUT, else upload session

_drive_cache: dict[str, str] = {}  # {"drive_id": ...}


class SharePointError(RuntimeError):
    pass


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _resolve_drive(token: str) -> str:
    """Return the target drive (document library) id, resolving + caching it."""
    if "drive_id" in _drive_cache:
        return _drive_cache["drive_id"]

    site = settings.sharepoint_site.strip()
    with httpx.Client(timeout=_TIMEOUT) as c:
        # Resolve the site id: explicit "hostname:/sites/Name" path, else search by name.
        if ":" in site or "/" in site:
            r = c.get(f"{GRAPH}/sites/{site}", headers=_headers(token))
            _raise_for(r, "resolve SharePoint site")
            site_id = r.json()["id"]
        else:
            r = c.get(f"{GRAPH}/sites", params={"search": site}, headers=_headers(token))
            _raise_for(r, "search SharePoint site")
            matches = r.json().get("value", [])
            chosen = next(
                (s for s in matches if s.get("name", "").lower() == site.lower()),
                matches[0] if matches else None,
            )
            if not chosen:
                raise SharePointError(f"SharePoint site '{site}' not found")
            site_id = chosen["id"]

        # Resolve the drive: named library, else the site's default drive.
        if settings.sharepoint_library:
            r = c.get(f"{GRAPH}/sites/{site_id}/drives", headers=_headers(token))
            _raise_for(r, "list SharePoint libraries")
            drives = r.json().get("value", [])
            drive = next(
                (d for d in drives if d.get("name", "").lower() == settings.sharepoint_library.lower()),
                None,
            )
            if not drive:
                raise SharePointError(f"Document library '{settings.sharepoint_library}' not found")
            drive_id = drive["id"]
        else:
            r = c.get(f"{GRAPH}/sites/{site_id}/drive", headers=_headers(token))
            _raise_for(r, "resolve default drive")
            drive_id = r.json()["id"]

    _drive_cache["drive_id"] = drive_id
    logger.info("SharePoint drive resolved for site %s", site)
    return drive_id


def _raise_for(r: httpx.Response, what: str) -> None:
    if r.status_code >= 400:
        raise SharePointError(f"Graph error ({what}): {r.status_code} {r.text[:300]}")


def upload(token: str, path: str, data: bytes, content_type: str) -> str:
    """Upload bytes to `path` within the drive; return the created item id."""
    drive_id = _resolve_drive(token)
    with httpx.Client(timeout=_TIMEOUT) as c:
        if len(data) <= _SIMPLE_MAX:
            r = c.put(
                f"{GRAPH}/drives/{drive_id}/root:/{path}:/content",
                headers={**_headers(token), "Content-Type": content_type},
                content=data,
            )
            _raise_for(r, "upload file")
            return r.json()["id"]

        # Large file (e.g. video): resumable upload session.
        r = c.post(
            f"{GRAPH}/drives/{drive_id}/root:/{path}:/createUploadSession",
            headers=_headers(token),
            json={"item": {"@microsoft.graph.conflictBehavior": "replace"}},
        )
        _raise_for(r, "create upload session")
        upload_url = r.json()["uploadUrl"]
        total = len(data)
        for start in range(0, total, _CHUNK):
            chunk = data[start:start + _CHUNK]
            end = start + len(chunk) - 1
            rr = c.put(
                upload_url,
                headers={
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {start}-{end}/{total}",
                },
                content=chunk,
            )
            if rr.status_code not in (200, 201, 202):
                _raise_for(rr, "upload chunk")
            if rr.status_code in (200, 201):
                return rr.json()["id"]
    raise SharePointError("Upload session completed without returning an item id")


def download(token: str, item_id: str) -> bytes:
    """Download an item's bytes by id."""
    with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as c:
        r = c.get(f"{GRAPH}/drives/{_resolve_drive(token)}/items/{item_id}/content",
                  headers=_headers(token))
        _raise_for(r, "download file")
        return r.content


def download_url(token: str, item_id: str) -> str | None:
    """Return a short-lived pre-authenticated download URL (good for streaming video)."""
    with httpx.Client(timeout=_TIMEOUT) as c:
        r = c.get(
            f"{GRAPH}/drives/{_resolve_drive(token)}/items/{item_id}",
            params={"select": "id,@microsoft.graph.downloadUrl"},
            headers=_headers(token),
        )
        _raise_for(r, "get download url")
        return r.json().get("@microsoft.graph.downloadUrl")


def delete(token: str, item_id: str) -> None:
    with httpx.Client(timeout=_TIMEOUT) as c:
        r = c.delete(f"{GRAPH}/drives/{_resolve_drive(token)}/items/{item_id}",
                     headers=_headers(token))
        if r.status_code not in (204, 404):
            _raise_for(r, "delete file")
