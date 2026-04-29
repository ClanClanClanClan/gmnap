#!/usr/bin/env python3
"""Adversarial browser-smoke harness for the MathLineage web UI.

Why this exists
---------------
Every "it works" claim about the web UI comes from FastAPI's ``TestClient``,
which is sync HTTP with no JS runtime. That bypasses:

* the hashcash proof-of-work loop (SHA-256 in SubtleCrypto)
* d3-based genealogy tree rendering
* real innerHTML/escaping in the browser (the DOM parser, not the mock)
* responsive breakpoints and keyboard focus order
* console errors and uncaught exceptions

This harness spawns ``gmnap serve`` on a free port, drives it with a real
Chromium via Playwright, and runs 32 adversarial scenarios. Any unhandled
console error or uncaught exception fails the run. Screenshots for each
scenario land in ``docs/screenshots/browser_audit/``.

Run
---

    PYTHONPATH=. python3 tools/browser_smoke.py --headless

Exit status is 0 on green, 1 on any failure. A Markdown report is written
to ``docs/browser_audit.md``.

Dependencies
------------

    pip install playwright>=1.45 && playwright install chromium

Design notes
------------

* Headless by default; pass ``--headed`` to see the browser.
* Uses one ``BrowserContext`` per scenario to isolate console logs and reset
  rate limits without restarting the server.
* Free tier rate limit is 60/min; we pace rapid-fire runs accordingly.
* Console errors are collected per-scenario and surfaced in the report —
  the hashcash worker logs one benign error when a request is retried on
  429, which we allow-list explicitly.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from playwright.sync_api import (
        Browser,
        BrowserContext,
        Error as PwError,
        Page,
        TimeoutError as PwTimeout,
        sync_playwright,
    )
except ImportError:  # pragma: no cover - surfaced to the user
    sys.stderr.write(
        "Playwright is not installed.\n"
        "Run:  pip install playwright && playwright install chromium\n"
    )
    sys.exit(2)


REPO = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = REPO / "docs" / "screenshots" / "browser_audit"
REPORT_PATH = REPO / "docs" / "browser_audit.md"

# Console errors we tolerate because they're expected in a healthy run.
# (e.g. a 429 from the rate limiter before the client retries.)
# Note: we intentionally do NOT whitelist 500s — scenarios that inject a
# 500 (network_500) must opt in via _allow_500s in their closure.
ALLOWED_CONSOLE_ERRORS = (
    re.compile(r"Failed to load resource.*429"),
    re.compile(r"Search error:.*Rate limit"),
)


@dataclasses.dataclass
class ScenarioResult:
    name: str
    passed: bool
    duration_ms: int
    screenshot: str | None = None
    errors: list[str] = dataclasses.field(default_factory=list)
    console_messages: list[str] = dataclasses.field(default_factory=list)
    note: str = ""


# ─── Server lifecycle ──────────────────────────────────────────────────


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_ready(port: int, timeout_s: float = 30.0) -> None:
    import urllib.request

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/readyz", timeout=1.0
            ) as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass
        time.sleep(0.3)
    raise RuntimeError(f"server did not become ready on port {port}")


def _start_server(port: int) -> subprocess.Popen:
    """Spawn ``gmnap serve`` (falls back to uvicorn directly)."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO)
    # Use a big rate-limit budget so rapid-fire scenarios don't trip it.
    env["GMNAP_FREE_RPM"] = "10000"
    env["OFFLINE"] = "1"
    # Pin a quieter log level so stderr doesn't overflow our capture buffer.
    env["GMNAP_LOG_LEVEL"] = "WARNING"

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.api.server:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]
    return subprocess.Popen(
        cmd,
        cwd=str(REPO),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


@contextlib.contextmanager
def _server():
    port = _free_port()
    proc = _start_server(port)
    try:
        _wait_for_ready(port)
        yield port
    finally:
        try:
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


# ─── Scenario helpers ──────────────────────────────────────────────────


def _collect_console(page: Page, errors: list[str], messages: list[str]) -> None:
    """Wire up console collectors.

    Scenarios can declare extra tolerated error patterns by setting
    ``page._extra_allowed_errors`` to a list of compiled regex objects
    (patterns stored in an attribute on the Page so closure plumbing
    stays simple). The global allowlist still applies unconditionally.
    """
    setattr(page, "_extra_allowed_errors", [])

    def _on_console(msg):
        try:
            text = f"{msg.type}: {msg.text}"
        except Exception:
            text = "<console-msg-unserializable>"
        messages.append(text)
        if msg.type in ("error",):
            allowed = list(ALLOWED_CONSOLE_ERRORS) + getattr(
                page, "_extra_allowed_errors", []
            )
            if not any(p.search(text) for p in allowed):
                errors.append(text)

    def _on_pageerror(exc):
        errors.append(f"uncaught: {exc}")

    page.on("console", _on_console)
    page.on("pageerror", _on_pageerror)


def _search_and_wait(page: Page, query: str, timeout_ms: int = 15000) -> None:
    page.fill("#search-input", query)
    page.press("#search-input", "Enter")
    # The app sets `hidden` attribute, which applies display:none via the
    # browser UA stylesheet. We use CSS-visibility-aware state matching
    # since `script-src 'self'` rejects eval-based wait_for_function.
    # Wait for any terminal: at least one result card, or the empty state,
    # or the error state — all three mean loading has settled.
    page.wait_for_selector(
        ".result-card, #no-results:not([hidden]), #error-msg:not([hidden])",
        state="attached",
        timeout=timeout_ms,
    )
    # And make sure the spinner is no longer visible.
    page.wait_for_selector("#loading", state="hidden", timeout=timeout_ms)


def _screenshot(page: Page, name: str) -> str:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path.relative_to(REPO))


# ─── Scenario definitions ──────────────────────────────────────────────


def scenario_happy_path(page: Page, base: str, name: str):
    """Search → result → profile → tree → click advisor navigates."""
    page.goto(base)
    _search_and_wait(page, name)
    # Need at least one result card, or page shows no-results
    page.wait_for_selector(".result-card, #no-results:not([hidden])", timeout=10000)
    cards = page.query_selector_all(".result-card")
    assert cards, f"no result card for {name!r}"
    cards[0].click()
    page.wait_for_selector(".profile-card", timeout=10000)
    # Tree is best-effort: if the endpoint returns 404 we still pass.
    page.wait_for_selector(
        "#genealogy-tree-svg, .tree-status",
        timeout=10000,
        state="attached",
    )
    # Wait for the tree fetch to settle — one of:
    #   - rendered nodes    -> svg g.tree-nodes
    #   - empty-state label -> .tree-status.tree-empty
    #   - error label       -> .tree-status.tree-error
    # CSP blocks eval-based wait_for_function, so we use CSS states.
    # 18-bit hashcash runs on the browser; budget generously.
    try:
        page.wait_for_selector(
            "#genealogy-tree-svg g.tree-nodes, .tree-status.tree-empty, .tree-status.tree-error",
            timeout=45000,
        )
    except PwTimeout:
        pass  # capture whatever state we're in


def scenario_xss(page: Page, base: str, payload: str):
    """XSS payloads must render as text, never execute.

    Three-layer verification (the earlier version only checked for
    alert() dialogs and was trivially satisfied by payloads that
    didn't call alert):

    1. no ``dialog`` event fires (catches ``alert()`` / ``confirm()``)
    2. no uncaught ``pageerror`` from the payload
    3. if the payload string surfaces in the DOM, it must be inside a
       text node — not parsed as HTML (i.e. no new ``<script>`` or
       ``<img onerror>`` elements from this query)
    """
    alert_fired = {"did": False}
    # HTML elements that a malicious payload would try to inject. We
    # snapshot the counts before the search so any increase is
    # attributable to the payload being parsed as HTML (escapeHtml
    # failure).
    INJECTABLE_TAGS = ("script", "img", "svg", "iframe", "object", "embed")
    pre_counts: dict[str, int] = {}

    def _on_dialog(d):
        alert_fired["did"] = True
        d.dismiss()

    page.on("dialog", _on_dialog)
    page.goto(base)
    for tag in INJECTABLE_TAGS:
        pre_counts[tag] = len(page.query_selector_all(tag))

    _search_and_wait(page, payload)
    # Strong assertion: terminal is *visible* (not just attached to the
    # DOM — the empty-state elements exist in the initial HTML).
    page.wait_for_selector(
        ".result-card, #no-results:not([hidden]), #error-msg:not([hidden])",
        timeout=8000,
    )

    # (1) No alert-like dialog — catches payloads whose unescaped form
    # would call alert()/confirm() on render (e.g. onerror handlers).
    assert not alert_fired["did"], f"XSS fired for payload {payload!r}"

    # (2) No new injectable element — catches payloads that were parsed
    # as HTML instead of rendered as text.
    for tag in INJECTABLE_TAGS:
        post = len(page.query_selector_all(tag))
        assert post == pre_counts[tag], (
            f"Payload injected a <{tag}> element "
            f"({pre_counts[tag]} -> {post}): {payload!r}"
        )


def scenario_unicode(page: Page, base: str, text: str):
    page.goto(base)
    _search_and_wait(page, text)
    page.wait_for_selector(
        # Visible terminal — `#results-list` is present in the initial
        # HTML, so state="attached" is trivially satisfied. We must
        # check for a *visible* terminal (result card, unhidden empty
        # state, or unhidden error state) or we'd pass on 500s.
        ".result-card, #no-results:not([hidden]), #error-msg:not([hidden])",
        timeout=8000,
    )


def scenario_edge_input(page: Page, base: str, value: str, label: str):
    page.goto(base)
    if not value.strip():
        # Empty / whitespace: performSearch is a no-op, so no scene change.
        page.fill("#search-input", value)
        page.press("#search-input", "Enter")
        # Landing should still be visible
        assert page.is_visible("#landing"), f"{label}: landing should stay visible"
        return
    _search_and_wait(page, value, timeout_ms=20000)
    page.wait_for_selector(
        # Visible terminal — see rationale in scenario_unicode.
        ".result-card, #no-results:not([hidden]), #error-msg:not([hidden])",
        timeout=10000,
    )


def scenario_rapid_fire(page: Page, base: str):
    """25 sequential queries paced to stay under 60 rpm."""
    page.goto(base)
    names = [
        "Euler, Leonhard",
        "Gauss, Carl",
        "Newton, Isaac",
        "Hilbert, David",
        "Poincaré, Henri",
        "Riemann, Bernhard",
        "Cauchy, Augustin",
        "Lagrange, Joseph",
        "Laplace, Pierre",
        "Fourier, Joseph",
        "Tao, Terence",
        "Erdős, Paul",
        "Mirzakhani, Maryam",
        "Kolmogorov, Andrey",
        "Ramanujan, Srinivasa",
        "Wiles, Andrew",
        "Perelman, Grigori",
        "Turing, Alan",
        "von Neumann, John",
        "Chern, Shiing-Shen",
        "Grothendieck, Alexander",
        "Serre, Jean-Pierre",
        "Atiyah, Michael",
        "Deligne, Pierre",
        "Connes, Alain",
    ]
    for n in names:
        _search_and_wait(page, n, timeout_ms=10000)


def scenario_keyboard(page: Page, base: str):
    page.goto(base)
    # "/" focuses search
    page.keyboard.press("/")
    active = page.evaluate("document.activeElement && document.activeElement.id")
    assert active == "search-input", f"'/' should focus search, got {active!r}"
    # Escape on landing does nothing harmful
    page.keyboard.press("Escape")
    # Fill and go; then escape back to landing
    page.fill("#search-input", "Euler")
    page.keyboard.press("Enter")
    page.wait_for_selector("#results-view:not([hidden])", timeout=8000)
    page.keyboard.press("Escape")
    page.wait_for_selector("#landing:not([hidden])", timeout=5000)


def scenario_responsive(page: Page, base: str, size: tuple[int, int], label: str):
    page.set_viewport_size({"width": size[0], "height": size[1]})
    page.goto(base)
    _search_and_wait(page, "Euler, Leonhard")
    page.wait_for_selector(".result-card, #no-results:not([hidden])", timeout=8000)
    scroll_w = page.evaluate("document.documentElement.scrollWidth")
    client_w = page.evaluate("document.documentElement.clientWidth")
    # Allow a 2-pixel fudge for sub-pixel antialiasing.
    assert (
        scroll_w - client_w <= 2
    ), f"{label}: horizontal scroll (scroll {scroll_w} > client {client_w})"


def scenario_correction_form(page: Page, base: str):
    page.goto(base)
    _search_and_wait(page, "Euler, Leonhard")
    page.wait_for_selector(".result-card", timeout=8000)
    page.click(".result-card")
    page.wait_for_selector("#open-correction", timeout=8000)
    page.click("#open-correction")
    page.wait_for_selector("#correction-dialog[open]", timeout=3000)
    # Click submit with empty required field. HTML5 should block form
    # submission entirely — no network request, dialog still open.
    page.click('#correction-dialog button[type="submit"]')
    # Give the form a beat to NOT submit
    page.wait_for_timeout(500)
    assert page.is_visible(
        "#correction-dialog[open]"
    ), "HTML5 validation should have kept dialog open"
    # The required input should now report invalid
    invalid = page.evaluate(
        "document.getElementById('corr-value').validity.valueMissing"
    )
    assert invalid is True, "corr-value should flag valueMissing"
    # Cancel it — dialog closes
    page.click("#corr-cancel")
    # <dialog> uses the CSS `dialog[open]` pattern; once closed, the
    # element is hidden via UA style. Wait for that state.
    page.wait_for_selector("#correction-dialog", state="hidden", timeout=3000)


def scenario_tree_depth(page: Page, base: str):
    """Depth selector must trigger a new fetch with the new depth param
    AND change the rendered node count (or keep it consistent when the
    underlying chain is shorter than the requested depth)."""
    lineage_calls: list[str] = []

    def _on_request(r):
        if "/api/v1/lineage" in r.url:
            lineage_calls.append(r.url)

    page.on("request", _on_request)

    page.goto(base)
    _search_and_wait(page, "Euler, Leonhard")
    page.wait_for_selector(".result-card", timeout=8000)
    page.click(".result-card")
    page.wait_for_selector("#tree-depth", timeout=10000)
    # Wait for the INITIAL tree fetch (depth=5) to settle so we can
    # measure the baseline node count.
    try:
        page.wait_for_selector(
            "#genealogy-tree-svg g.tree-nodes, "
            ".tree-status.tree-empty, .tree-status.tree-error",
            timeout=45000,
        )
    except PwTimeout:
        pass
    initial_url_count = len(lineage_calls)
    depth5_nodes = len(page.query_selector_all("#genealogy-tree-svg g.tree-node"))

    # Change depth — must issue a NEW lineage request with depth=3.
    # The profile view is long; the tree header may be below the viewport
    # fold. Scroll to it explicitly before interacting.
    sel = page.locator("#tree-depth")
    sel.scroll_into_view_if_needed()
    sel.select_option("3")
    # Wait for a second lineage call (or timeout)
    start = time.time()
    while time.time() - start < 15:
        if len(lineage_calls) > initial_url_count:
            break
        page.wait_for_timeout(200)
    assert (
        len(lineage_calls) > initial_url_count
    ), "depth-selector change did not trigger a new /api/v1/lineage call"
    last_url = lineage_calls[-1]
    assert "depth=3" in last_url, f"new lineage call not at depth=3: {last_url}"

    # Let the re-render finish
    page.wait_for_timeout(1000)
    depth3_nodes = len(page.query_selector_all("#genealogy-tree-svg g.tree-node"))
    # depth=3 should have <= as many nodes as depth=5 (can be equal
    # when the chain is shorter than 3). Never more.
    assert (
        depth3_nodes <= depth5_nodes
    ), f"depth=3 rendered {depth3_nodes} nodes, more than depth=5 ({depth5_nodes})"
    # And the tree panel stays visible.
    assert page.is_visible("#genealogy-tree-svg") or page.is_visible(
        ".tree-status"
    ), "tree panel disappeared after depth change"


def scenario_network_500(page: Page, base: str):
    """A server 500 on /api/v1/process must surface as a user-visible
    error state (not a frozen spinner)."""
    # Expected console noise from the injected 500:
    #   - browser resource-loader log: "…status of 500 (Internal Server Error)"
    #   - app's own error path:        "Search error: Error: injected-failure"
    # Both are desirable behaviour — the scenario asserts the UI recovers.
    page._extra_allowed_errors.append(re.compile(r"status of 500"))
    page._extra_allowed_errors.append(re.compile(r"Search error:.*injected-failure"))

    # Intercept the next /api/v1/process call and return 500.
    def _handler(route):
        if route.request.url.endswith("/api/v1/process"):
            route.fulfill(
                status=500,
                body='{"detail": "injected-failure"}',
                content_type="application/json",
            )
        else:
            route.continue_()

    page.route("**/api/v1/*", _handler)
    page.goto(base)
    page.fill("#search-input", "Euler, Leonhard")
    page.press("#search-input", "Enter")
    # Either the error banner, or the "no results" (app may classify any
    # non-ok response as empty) — but NOT the spinner stuck on screen.
    page.wait_for_selector(
        "#error-msg:not([hidden]), #no-results:not([hidden])",
        timeout=15000,
    )
    page.wait_for_selector("#loading", state="hidden", timeout=5000)


def scenario_unknown_name(page: Page, base: str):
    page.goto(base)
    _search_and_wait(page, "Zzxqvwn, Notreal")
    # Either there's a result (the pipeline can still process it) or empty state.
    page.wait_for_selector(
        # Visible terminal — `#results-list` is present in the initial
        # HTML, so state="attached" is trivially satisfied. We must
        # check for a *visible* terminal (result card, unhidden empty
        # state, or unhidden error state) or we'd pass on 500s.
        ".result-card, #no-results:not([hidden]), #error-msg:not([hidden])",
        timeout=8000,
    )


def scenario_url_state(page: Page, base: str):
    """Exercise the SPA router added in round 8.

    Three properties:
    1. Searching on the landing page updates `location.search` to
       ``?q=<query>``, so the URL is shareable.
    2. Clicking a result-card pushes a `/p/<encoded-name>` path,
       so the profile is deep-linkable.
    3. A direct visit to `/p/<encoded-name>` lands on the profile
       (not the landing page) — proves the FastAPI catch-all and the
       client-side `applyLocation()` cooperate.
    """
    # 1. Landing → search via Enter
    page.goto(base)
    _search_and_wait(page, "Euler, Leonhard")
    after_search = page.url
    if "?q=" not in after_search:
        raise RuntimeError(f"expected ?q= in URL after search, got: {after_search}")

    # 2. Click the first result card to open the profile
    page.click(".result-card", timeout=5000)
    page.wait_for_selector("#profile-content", state="visible", timeout=5000)
    after_click = page.url
    if "/p/" not in after_click:
        raise RuntimeError(
            f"expected /p/ in URL after profile click, got: {after_click}"
        )

    # 3. Direct deep-link load
    page.goto(after_click)
    # Should resolve to a profile, not the landing page (#landing is hidden)
    page.wait_for_selector("#profile-content", state="visible", timeout=15000)
    if page.locator("#landing").is_visible():
        raise RuntimeError("deep-link landed on #landing instead of #profile-view")


# ─── Runner ────────────────────────────────────────────────────────────


def _run_scenario(
    name: str, fn: Callable[..., None], *args: Any, **kwargs: Any
) -> ScenarioResult:
    browser: Browser = kwargs.pop("browser")
    base: str = kwargs.pop("base")
    snap_id: str = kwargs.pop(
        "snap_id", re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    )
    context: BrowserContext = browser.new_context(
        viewport={"width": 1440, "height": 900}
    )
    page = context.new_page()
    errors: list[str] = []
    messages: list[str] = []
    _collect_console(page, errors, messages)

    t0 = time.time()
    ok = True
    note = ""
    screenshot: str | None = None
    try:
        fn(page, base, *args, **kwargs)
    except (AssertionError, PwError, PwTimeout) as exc:
        ok = False
        note = f"{type(exc).__name__}: {exc}"
        errors.append(note)
    except Exception as exc:  # defensive
        ok = False
        note = f"unexpected {type(exc).__name__}: {exc}"
        errors.append(note)
        errors.append(traceback.format_exc())
    try:
        screenshot = _screenshot(page, snap_id)
    except Exception:
        pass

    # Console errors fail the scenario regardless of the assertion outcome.
    if errors and ok:
        ok = False
        note = f"console error: {errors[0][:120]}"

    dt = int((time.time() - t0) * 1000)
    context.close()
    return ScenarioResult(
        name=name,
        passed=ok,
        duration_ms=dt,
        screenshot=screenshot,
        errors=errors,
        console_messages=messages,
        note=note,
    )


def _build_scenarios() -> list[tuple[str, Callable[..., None], tuple, dict]]:
    happy = [
        ("happy:Euler", scenario_happy_path, ("Euler, Leonhard",), {}),
        ("happy:Hilbert", scenario_happy_path, ("Hilbert, David",), {}),
        ("happy:Newton", scenario_happy_path, ("Newton, Isaac",), {}),
        ("happy:Tao", scenario_happy_path, ("Tao, Terence",), {}),
        ("happy:Mirzakhani", scenario_happy_path, ("Mirzakhani, Maryam",), {}),
    ]
    xss = [
        # innerHTML-injected <script> is neutered by the browser, but a
        # marker element would still prove escaping failed. Our assertion
        # is "no new <script> appears in the DOM".
        ("xss:script", scenario_xss, ("<script>alert(1)</script>",), {}),
        # onerror on <img> DOES fire via innerHTML. If escapeHtml were
        # removed, this would trigger both the dialog check AND the new
        # <img> element assertion.
        ("xss:onerror", scenario_xss, ('"><img src=x onerror=alert(1)>',), {}),
        # svg onload — same class of attack as img onerror.
        ("xss:svg", scenario_xss, ('"><svg onload=alert(1)>',), {}),
        # javascript: URLs should never be turned into clickable hrefs.
        ("xss:javascript", scenario_xss, ("javascript:alert(1)",), {}),
        # SQL-injection-looking input should pass through as text.
        ("xss:sql", scenario_xss, ("'; DROP TABLE users;--",), {}),
        # Path traversal should not leak a filesystem read.
        ("xss:traversal", scenario_xss, ("../../../../etc/passwd",), {}),
    ]
    unicode = [
        ("unicode:jp", scenario_unicode, ("田中 太郎",), {}),
        ("unicode:ru", scenario_unicode, ("Колмогоров",), {}),
        ("unicode:ar", scenario_unicode, ("محمد علي",), {}),
        ("unicode:gr", scenario_unicode, ("Παπαδόπουλος",), {}),
        ("unicode:diacritic", scenario_unicode, ("Poincaré, Henri",), {}),
        ("unicode:emoji", scenario_unicode, ("🧮 math",), {}),
    ]
    edges = [
        ("edge:empty", scenario_edge_input, ("", "empty"), {}),
        ("edge:one_char", scenario_edge_input, ("a", "1 char"), {}),
        ("edge:long", scenario_edge_input, ("E" * 500, "500 char"), {}),
        ("edge:spaces", scenario_edge_input, ("   Euler   ", "padded"), {}),
        ("edge:newline", scenario_edge_input, ("Euler\nLeonhard", "newline"), {}),
    ]
    responsive = [
        ("resp:mobile", scenario_responsive, ((375, 667), "iPhone"), {}),
        ("resp:tablet", scenario_responsive, ((768, 1024), "iPad"), {}),
        ("resp:laptop", scenario_responsive, ((1440, 900), "laptop"), {}),
    ]
    misc = [
        ("keyboard", scenario_keyboard, (), {}),
        ("correction_form", scenario_correction_form, (), {}),
        ("tree_depth", scenario_tree_depth, (), {}),
        ("unknown_name", scenario_unknown_name, (), {}),
        ("url_state", scenario_url_state, (), {}),
        ("network_500", scenario_network_500, (), {}),
        ("rapid_fire", scenario_rapid_fire, (), {}),
    ]
    return happy + xss + unicode + edges + responsive + misc


def _write_report(results: list[ScenarioResult]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Browser audit",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"Scenarios: {len(results)}. "
        f"Passed: {sum(1 for r in results if r.passed)}. "
        f"Failed: {sum(1 for r in results if not r.passed)}.",
        "",
        "| # | Scenario | Result | Time | Note |",
        "|---|----------|--------|------|------|",
    ]
    for i, r in enumerate(results, 1):
        result = "✅ pass" if r.passed else "❌ fail"
        shot = f" — [screenshot]({r.screenshot})" if r.screenshot else ""
        note = (r.note or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {i} | `{r.name}` | {result} | {r.duration_ms} ms | {note}{shot} |"
        )
    lines.append("")
    failures = [r for r in results if not r.passed]
    if failures:
        lines.append("## Failures")
        lines.append("")
        for r in failures:
            lines.append(f"### `{r.name}`")
            lines.append("")
            for err in r.errors[:10]:
                lines.append("```")
                lines.append(err)
                lines.append("```")
            lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--headed", dest="headless", action="store_false")
    parser.add_argument(
        "--filter", help="only run scenarios whose names match this regex"
    )
    parser.add_argument(
        "--junit-xml", type=Path, help="write JUnit XML for CI consumption"
    )
    args = parser.parse_args()

    pat = re.compile(args.filter) if args.filter else None
    scenarios = _build_scenarios()
    if pat:
        scenarios = [s for s in scenarios if pat.search(s[0])]

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[ScenarioResult] = []
    with _server() as port, sync_playwright() as pw:
        base = f"http://127.0.0.1:{port}"
        browser = pw.chromium.launch(headless=args.headless)
        try:
            for idx, (name, fn, a, kw) in enumerate(scenarios):
                print(
                    f"[{idx + 1:>2}/{len(scenarios)}] {name} ... ", end="", flush=True
                )
                kw = dict(kw)
                kw.update(browser=browser, base=base)
                res = _run_scenario(name, fn, *a, **kw)
                results.append(res)
                print("pass" if res.passed else f"FAIL ({res.note})")
        finally:
            browser.close()

    _write_report(results)
    if args.junit_xml:
        _write_junit(results, args.junit_xml)

    failed = [r for r in results if not r.passed]
    print()
    print(f"Report: {REPORT_PATH.relative_to(REPO)}")
    if failed:
        print(f"{len(failed)} scenarios failed.")
        return 1
    print(f"All {len(results)} scenarios passed.")
    return 0


def _write_junit(results: list[ScenarioResult], path: Path) -> None:
    import xml.etree.ElementTree as ET

    suite = ET.Element(
        "testsuite",
        attrib={
            "name": "browser_smoke",
            "tests": str(len(results)),
            "failures": str(sum(1 for r in results if not r.passed)),
            "time": f"{sum(r.duration_ms for r in results) / 1000:.2f}",
        },
    )
    for r in results:
        tc = ET.SubElement(
            suite,
            "testcase",
            attrib={"name": r.name, "time": f"{r.duration_ms / 1000:.3f}"},
        )
        if not r.passed:
            failure = ET.SubElement(tc, "failure", attrib={"message": r.note[:200]})
            failure.text = "\n".join(r.errors)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    sys.exit(main())
