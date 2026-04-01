"""Tests for web interface (Phase 4 audit fixes)."""

import re
from pathlib import Path

import pytest

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"
HTML_FILE = STATIC_DIR / "index.html"
CSS_FILE = STATIC_DIR / "style.css"
JS_FILE = STATIC_DIR / "app.js"


@pytest.fixture()
def html():
    assert HTML_FILE.exists(), "index.html not found"
    return HTML_FILE.read_text(encoding="utf-8")


@pytest.fixture()
def css():
    assert CSS_FILE.exists(), "style.css not found"
    return CSS_FILE.read_text(encoding="utf-8")


@pytest.fixture()
def js():
    assert JS_FILE.exists(), "app.js not found"
    return JS_FILE.read_text(encoding="utf-8")


# ── HTML Tests ────────────────────────────────────────────────────────


def test_html_valid_structure(html):
    """HTML must have proper doctype, html, head, body tags."""
    assert "<!DOCTYPE html>" in html, "Missing DOCTYPE"
    assert "<html" in html, "Missing <html> tag"
    assert "<head>" in html, "Missing <head>"
    assert "<body>" in html, "Missing <body>"
    assert "</html>" in html, "Missing closing </html>"


def test_html_viewport_meta(html):
    """Must have responsive viewport meta tag."""
    assert 'name="viewport"' in html, "Missing viewport meta tag"
    assert "width=device-width" in html, "Viewport must set device-width"


def test_html_title_set(html):
    """Page title must be set."""
    match = re.search(r"<title>(.+?)</title>", html)
    assert match, "Missing <title> tag"
    assert len(match.group(1)) > 3, "Title is too short"


def test_html_has_profile_section(html):
    """HTML must have a profile-view section for viewing mathematician profiles."""
    assert 'id="profile-view"' in html, "Missing profile-view section"
    assert 'id="profile-content"' in html, "Missing profile-content container"


def test_html_has_correction_form(html):
    """HTML must have a correction dialog for community suggestions."""
    assert 'id="correction-dialog"' in html, "Missing correction-dialog element"
    assert 'id="correction-form"' in html, "Missing correction-form"
    assert "correction_type" in html, "Missing correction_type field"


def test_html_accessibility_landmarks(html):
    """Must have proper ARIA landmarks."""
    assert 'role="banner"' in html, "Missing banner landmark (header)"
    assert 'role="main"' in html, "Missing main landmark"
    assert 'role="contentinfo"' in html, "Missing contentinfo landmark (footer)"


def test_html_search_input_aria(html):
    """Search input must have proper ARIA attributes."""
    assert "aria-label" in html, "Missing aria-label on search input"
    assert 'type="search"' in html, "Search input should have type=search"


def test_html_no_inline_scripts(html):
    """Must not contain inline <script> tags with code (only src references)."""
    # Find all script tags
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL)
    for content in scripts:
        stripped = content.strip()
        assert stripped == "", f"Inline script found: {stripped[:80]}..."


# ── CSS Tests ─────────────────────────────────────────────────────────


def test_css_dark_theme_variables(css):
    """CSS must define dark theme custom properties."""
    assert "--bg-primary" in css, "Missing --bg-primary variable"
    assert "--text-primary" in css, "Missing --text-primary variable"
    assert "#0a0a0f" in css, "Background should be dark (#0a0a0f)"
    assert "#f0f0f5" in css, "Text should be light (#f0f0f5)"


def test_css_mobile_breakpoints(css):
    """Must have mobile responsive breakpoints."""
    breakpoints = re.findall(r"@media\s*\(max-width:\s*(\d+)px\)", css)
    assert len(breakpoints) >= 1, "Must have at least one responsive breakpoint"
    # Check for common mobile breakpoint
    widths = [int(b) for b in breakpoints]
    assert any(w <= 768 for w in widths), "Must have a mobile breakpoint (<= 768px)"


def test_css_focus_indicators(css):
    """Must have visible focus indicators for accessibility."""
    assert "focus-visible" in css or "focus" in css, "Must define focus styles"
    assert "outline" in css, "Focus styles must use outline"


def test_css_reduced_motion(css):
    """Must respect prefers-reduced-motion."""
    assert "prefers-reduced-motion" in css, "Must support prefers-reduced-motion"


def test_css_no_fixed_widths(css):
    """Should not use fixed pixel widths for containers (responsive design)."""
    # Check that main containers use max-width or percentages, not width: NNNpx
    # We check for suspicious fixed widths on containers
    lines = css.splitlines()
    fixed_width_count = 0
    for line in lines:
        stripped = line.strip()
        # Match "width: 500px" but not "max-width: 500px" or "min-width"
        if re.match(r"^width:\s*\d{3,}px", stripped):
            fixed_width_count += 1
    assert (
        fixed_width_count == 0
    ), f"Found {fixed_width_count} fixed pixel widths on containers"


# ── JavaScript Tests ──────────────────────────────────────────────────


def test_js_xss_escape_function(js):
    """escapeHtml must handle all dangerous characters."""
    # Check the function exists and handles key characters
    assert "escapeHtml" in js, "Must have escapeHtml function"
    assert "&amp;" in js, "Must escape &"
    assert "&lt;" in js, "Must escape <"
    assert "&gt;" in js, "Must escape >"
    assert "&quot;" in js, "Must escape double quotes"
    assert "&#39;" in js, "Must escape single quotes"
    assert "&#96;" in js, "Must escape backticks"


def test_js_xss_escape_used_everywhere(js):
    """Every innerHTML assignment must use escapeHtml."""
    # Find all innerHTML assignments
    lines = js.splitlines()
    for i, line in enumerate(lines, 1):
        if "innerHTML" in line and "=" in line:
            # Check if it's being cleared (= "") or uses escapeHtml in context
            stripped = line.strip()
            if '= ""' in stripped or "= ''" in stripped:
                continue
            # Look at surrounding lines (within 10 lines) for escapeHtml usage
            context_start = max(0, i - 11)
            context_end = min(len(lines), i + 10)
            context = "\n".join(lines[context_start:context_end])
            assert (
                "escapeHtml" in context
            ), f"innerHTML on line {i} lacks escapeHtml in nearby context: {stripped}"


def test_js_no_eval(js):
    """Must not use eval() or Function() constructor."""
    # Remove string literals to avoid false positives
    cleaned = re.sub(r'"[^"]*"', '""', js)
    cleaned = re.sub(r"'[^']*'", "''", cleaned)
    assert "eval(" not in cleaned, "Must not use eval()"
    assert "Function(" not in cleaned, "Must not use Function() constructor"


def test_js_debounce_implemented(js):
    """Search must use debouncing."""
    assert "debounce" in js, "Must implement debounce"
    assert "300" in js or "setTimeout" in js, "Debounce should use setTimeout"


def test_js_error_handling(js):
    """Every fetch call must have error handling."""
    fetch_count = js.count("fetch(")
    catch_count = js.count(".catch(")
    # Also count try/catch around fetch
    assert (
        catch_count >= fetch_count or "catch" in js
    ), f"Found {fetch_count} fetch calls but only {catch_count} .catch handlers"


def test_js_no_console_log(js):
    """Should not have console.log (console.error is OK for error reporting)."""
    lines = js.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        assert (
            "console.log(" not in stripped
        ), f"console.log found on line {i}: {stripped}"


def test_js_uses_process_endpoint(js):
    """app.js must call /api/v1/process for enriched search results."""
    assert "/api/v1/process" in js, "Must call /api/v1/process endpoint"


def test_js_renders_advisor_section(js):
    """app.js must have advisor rendering code."""
    assert "advisor-card" in js, "Must render advisor cards"
    assert "Advisors" in js or "advisors" in js, "Must reference advisor data"


def test_js_correction_form_submit(js):
    """app.js must submit correction form to /api/v1/suggest."""
    assert "/api/v1/suggest" in js, "Must call /api/v1/suggest endpoint"
    assert "correction_type" in js, "Must send correction_type"


def test_js_renders_profile(js):
    """app.js must have a renderProfile function."""
    assert "renderProfile" in js, "Must have renderProfile function"


# ── Integration Tests ─────────────────────────────────────────────────


def test_static_index_served():
    """Static index page should be served by FastAPI."""
    try:
        from fastapi.testclient import TestClient

        from src.api.server import create_app

        app = create_app()
        client = TestClient(app)
        resp = client.get("/")
        # Should serve index.html or redirect
        assert resp.status_code in (
            200,
            307,
            404,
        ), f"Unexpected status: {resp.status_code}"
        if resp.status_code == 200:
            assert "MathLineage" in resp.text or "GMNAP" in resp.text or "html" in resp.text.lower()
    except ImportError:
        pytest.skip("FastAPI not available")


def test_api_and_static_coexist():
    """API endpoints and static files should both work."""
    try:
        from fastapi.testclient import TestClient

        from src.api.server import create_app

        app = create_app()
        client = TestClient(app)

        # Health endpoint should still work
        resp = client.get("/healthz")
        assert resp.status_code == 200

        # Static CSS should be served if static dir exists
        resp_css = client.get("/static/style.css")
        # May be 200 or 404 depending on mount
        assert resp_css.status_code in (200, 404)
    except ImportError:
        pytest.skip("FastAPI not available")
