"""Server-side HTML sanitization + plain-text extraction.

Defense in depth: we sanitize on ingest here AND render in a sandboxed iframe
on the client. The sanitized HTML is what gets stored/served; the raw upload is
never trusted.
"""
from __future__ import annotations

import bleach
from bs4 import BeautifulSoup

try:
    from bleach.css_sanitizer import CSSSanitizer

    _css_sanitizer: "CSSSanitizer | None" = CSSSanitizer()
except Exception:  # pragma: no cover - css extra not installed
    _css_sanitizer = None

# Tags whose entire contents must be discarded (not just the tag).
DANGEROUS_TAGS = ["script", "iframe", "object", "embed", "form", "noscript", "template"]

# Structural "chrome" tags removed *with their contents* on ingest. Authored
# reports often carry a top <header> banner (file name / version / date) that
# duplicates the metadata the portal already renders around the report, so we
# drop it from the stored HTML. Removed here, not for security.
STRIPPED_TAGS = ["header"]

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
        # <header> intentionally omitted — stripped with its contents (see STRIPPED_TAGS).
        "a", "section", "article", "footer", "nav", "aside", "main",
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
    # First drop dangerous + chrome tags *and their text* (bleach would keep the text).
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(DANGEROUS_TAGS + STRIPPED_TAGS):
        tag.decompose()
    cleaned = bleach.clean(
        str(soup),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=_css_sanitizer,
        strip=True,
        strip_comments=True,
    )
    return cleaned


def extract_text(html: str) -> str:
    """Return visible text for full-text indexing."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # collapse whitespace
    return " ".join(text.split())
