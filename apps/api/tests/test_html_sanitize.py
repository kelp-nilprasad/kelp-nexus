"""Unit tests for HTML sanitization (no DB required)."""
from app.services.html_sanitize import extract_text, sanitize_html


def test_strips_script_tags():
    dirty = "<p>Hello</p><script>alert('xss')</script>"
    clean = sanitize_html(dirty)
    assert "<script>" not in clean
    assert "alert" not in clean
    assert "Hello" in clean


def test_strips_javascript_uri():
    dirty = '<a href="javascript:alert(1)">click</a>'
    clean = sanitize_html(dirty)
    assert "javascript:" not in clean


def test_strips_event_handlers():
    dirty = '<img src="x" onerror="alert(1)">'
    clean = sanitize_html(dirty)
    assert "onerror" not in clean


def test_keeps_safe_formatting():
    dirty = "<h1>Title</h1><table><tr><td>cell</td></tr></table><pre><code>x=1</code></pre>"
    clean = sanitize_html(dirty)
    assert "<h1>" in clean and "<table>" in clean and "<code>" in clean


def test_extract_text_drops_markup():
    text = extract_text("<h1>Hi</h1><p>there <b>world</b></p>")
    assert text == "Hi there world"


def test_preserves_css_child_combinator_in_style():
    # <style> is a raw-text element: CSS must be emitted verbatim, never
    # entity-escaped. A `>` combinator turning into `&gt;` silently kills the rule.
    dirty = (
        "<style>.plain>div{display:grid;grid-template-columns:168px minmax(0,1fr)}"
        " .a>b{color:red}</style><h1>Hi</h1>"
    )
    clean = sanitize_html(dirty)
    assert "&gt;" not in clean
    assert ".plain>div" in clean and ".a>b" in clean


def test_preserves_multiple_style_blocks_and_special_chars():
    dirty = (
        "<style>a>b{x:1}</style><p>mid</p>"
        "<style>@media(max-width:600px){.g{display:none}} li:nth-child(2n){color:blue}</style>"
    )
    clean = sanitize_html(dirty)
    assert "a>b{x:1}" in clean
    assert "max-width:600px" in clean and "nth-child(2n)" in clean
    assert "KELPSTYLE" not in clean  # no placeholder token leaks into output


def test_css_preservation_does_not_weaken_sanitization():
    # Restoring <style> verbatim must not reopen an injection path.
    dirty = (
        "<style>.a>b{color:red}</style><script>steal()</script>"
        "<p onclick=\"evil()\">t</p><style>.c>d{x:1}</style>"
    )
    clean = sanitize_html(dirty)
    assert "steal()" not in clean and "<script" not in clean
    assert "onclick" not in clean
    assert ".a>b" in clean and ".c>d" in clean


def test_preserves_document_header_as_authored():
    # We must NOT strip the document's own <header> — reports render as authored.
    dirty = (
        "<header><div>KELP · STANDARD GUIDELINES</div>"
        "<span>SG-SKILL · V1.0 · JULY 2026</span></header>"
        "<main><h1>Skills are packages</h1><p>Body.</p></main>"
    )
    clean = sanitize_html(dirty)
    assert "<header>" in clean
    assert "SG-SKILL" in clean and "STANDARD GUIDELINES" in clean
    assert "Skills are packages" in clean
