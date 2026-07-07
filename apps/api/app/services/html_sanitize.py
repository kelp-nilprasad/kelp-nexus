"""Server-side HTML sanitization + plain-text extraction.

Defense in depth: we sanitize on ingest here AND render in a sandboxed iframe
on the client. The sanitized HTML is what gets stored/served; the raw upload is
never trusted.
"""
from __future__ import annotations

import secrets

import bleach
from bs4 import BeautifulSoup

try:
    from bleach.css_sanitizer import CSSSanitizer

    _css_sanitizer: "CSSSanitizer | None" = CSSSanitizer()
except Exception:  # pragma: no cover - css extra not installed
    _css_sanitizer = None

# Tags whose entire contents must be discarded (not just the tag).
# Security only — we do NOT strip any of the document's own visible content
# (e.g. <header>): uploaded reports render as authored.
DANGEROUS_TAGS = ["script", "iframe", "object", "embed", "form", "noscript", "template"]

# Permissive enough for rich technical reports, but no script/iframe/object/etc.
ALLOWED_TAGS = sorted(
    set(bleach.sanitizer.ALLOWED_TAGS)
    | {
        "p", "div", "span", "br", "hr", "pre", "code", "blockquote",
        "h1", "h2", "h3", "h4", "h5", "h6",
        "ul", "ol", "li", "dl", "dt", "dd",
        "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption", "colgroup", "col",
        "img", "figure", "figcaption", "picture",
        "strong", "em", "b", "i", "u", "s", "sup", "sub", "mark", "small",
        "a", "section", "article", "header", "footer", "nav", "aside", "main",
        "style",  # inline <style> allowed; scoped inside the sandboxed iframe
    }
)

ALLOWED_ATTRIBUTES = {
    "*": ["class", "id", "style", "title", "role", "aria-label", "colspan", "rowspan", "align"],
    "a": ["href", "target", "rel"],
    "img": ["src", "alt", "width", "height", "loading"],
    "col": ["span", "width"],
}

# Only http(s), data-image, and mailto — blocks javascript:/vbscript: URIs.
ALLOWED_PROTOCOLS = ["http", "https", "mailto", "data"]


def sanitize_html(raw: str) -> str:
    # First drop dangerous tags *and their text* (bleach would keep the text).
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(DANGEROUS_TAGS):
        tag.decompose()

    # <style> is a raw-text element: its CSS must be emitted verbatim. bleach
    # (html5lib) instead escapes the *contents*, turning `.a>b{}` into `.a&gt;b{}`
    # and silently breaking any rule using > < or &. Swap each block's CSS for an
    # opaque placeholder before bleach, then restore it byte-for-byte afterward.
    # This is safe: parsed <style> text can never contain "</style>", so there is
    # no way to break out of the element when we re-insert it.
    boundary = secrets.token_hex(16)
    placeholders: list[tuple[str, str]] = []
    for i, style in enumerate(soup.find_all("style")):
        css = style.string or ""
        token = f"KELPSTYLE{boundary}{i}"
        placeholders.append((token, css))
        style.string = token

    cleaned = bleach.clean(
        str(soup),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=_css_sanitizer,
        strip=True,
        strip_comments=True,
    )

    for token, css in placeholders:
        cleaned = cleaned.replace(token, css)
    return cleaned


def extract_text(html: str) -> str:
    """Return visible text for full-text indexing."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # collapse whitespace
    return " ".join(text.split())
