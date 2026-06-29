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
