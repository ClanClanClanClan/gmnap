#!/usr/bin/env python3
"""Capture canonical DEMO screenshots from the web UI.

Run with:  PYTHONPATH=. python3 tools/capture_screenshots.py

Spawns uvicorn on a free port, drives it with headless Chromium, and
writes the eight canonical flows referenced by ``DEMO.md`` into
``docs/screenshots/``. Idempotent — re-running overwrites.

Separate from ``tools/browser_smoke.py`` so the smoke harness can stay
focused on adversarial coverage while these shots stay under curatorial
control.
"""

from __future__ import annotations

import contextlib
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.stderr.write(
        "Playwright not installed.\n"
        "Run:  pip install playwright && playwright install chromium\n"
    )
    sys.exit(2)


REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "docs" / "screenshots"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_ready(port: int, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/readyz", timeout=1.0
            ) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(0.3)
    raise RuntimeError(f"server not ready on :{port}")


@contextlib.contextmanager
def _server():
    port = _free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO)
    env["GMNAP_FREE_RPM"] = "10000"
    env["OFFLINE"] = "1"
    env["GMNAP_LOG_LEVEL"] = "WARNING"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.server:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(REPO), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        _wait_ready(port)
        yield port
    finally:
        try:
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


# ─── Capture helpers ───────────────────────────────────────────────────


def _search_and_wait(page, query: str):
    page.fill("#search-input", query)
    page.press("#search-input", "Enter")
    page.wait_for_selector(
        ".result-card, #no-results:not([hidden]), #error-msg:not([hidden])",
        state="attached", timeout=20000,
    )
    page.wait_for_selector("#loading", state="hidden", timeout=20000)


def _open_profile(page, name: str):
    _search_and_wait(page, name)
    page.wait_for_selector(".result-card", timeout=15000)
    page.click(".result-card")
    page.wait_for_selector(".advisor-card, .profile-card", timeout=15000)


def _wait_tree(page):
    try:
        page.wait_for_selector(
            "#genealogy-tree-svg g.tree-nodes, "
            ".tree-status.tree-empty, .tree-status.tree-error",
            timeout=60000,
        )
    except Exception:
        pass


# ─── Shots ─────────────────────────────────────────────────────────────


def capture_all(base: str) -> list[tuple[str, Path]]:
    with sync_playwright() as p:
        b = p.chromium.launch()
        out: list[tuple[str, Path]] = []

        # Desktop 1440x900 shots
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        # 01 landing
        page.goto(base)
        page.wait_for_selector(".hero h1", timeout=10000)
        p01 = OUT_DIR / "01_landing.png"
        page.screenshot(path=str(p01), full_page=False)
        out.append(("Landing page", p01))

        # 02 search results
        _search_and_wait(page, "Euler, Leonhard")
        p02 = OUT_DIR / "02_search_results.png"
        page.screenshot(path=str(p02), full_page=False)
        out.append(("Search results", p02))

        # 03 profile (above-the-fold)
        page.click(".result-card")
        page.wait_for_selector(".advisor-card", timeout=15000)
        # Don't wait for tree — capture the profile header first
        p03 = OUT_DIR / "03_profile_euler.png"
        page.screenshot(path=str(p03), full_page=False)
        out.append(("Profile — Euler", p03))

        # 04 full profile with tree rendered
        _wait_tree(page)
        p04 = OUT_DIR / "04_tree_euler.png"
        page.screenshot(path=str(p04), full_page=True)
        out.append(("Profile + tree — Euler (depth 5)", p04))

        # 05 Hilbert multi-advisor (Hilbert has two advisors)
        page.goto(base)
        _open_profile(page, "Hilbert, David")
        _wait_tree(page)
        p05 = OUT_DIR / "05_tree_hilbert.png"
        page.screenshot(path=str(p05), full_page=True)
        out.append(("Profile + tree — Hilbert", p05))

        # 06 correction dialog
        page.goto(base)
        _open_profile(page, "Tao, T.")
        page.wait_for_selector("#open-correction", timeout=15000)
        page.click("#open-correction")
        page.wait_for_selector("#correction-dialog[open]", timeout=5000)
        p06 = OUT_DIR / "06_correction_dialog.png"
        page.screenshot(path=str(p06), full_page=False)
        out.append(("Correction dialog", p06))
        page.click("#corr-cancel")

        # 08 unknown name
        page.goto(base)
        _search_and_wait(page, "Zzxqvwn, Notreal")
        p08 = OUT_DIR / "08_unknown_name.png"
        page.screenshot(path=str(p08), full_page=False)
        out.append(("Unknown-name fallback", p08))
        ctx.close()

        # Mobile shot
        ctx = b.new_context(viewport={"width": 375, "height": 667})
        page = ctx.new_page()
        page.goto(base)
        _search_and_wait(page, "Euler, Leonhard")
        page.wait_for_selector(".result-card", timeout=15000)
        p07 = OUT_DIR / "07_mobile_viewport.png"
        page.screenshot(path=str(p07), full_page=True)
        out.append(("Mobile viewport (375×667)", p07))
        ctx.close()

        b.close()
        return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with _server() as port:
        base = f"http://127.0.0.1:{port}"
        shots = capture_all(base)
    print(f"\nCaptured {len(shots)} screenshots to {OUT_DIR}:")
    for label, path in shots:
        rel = path.relative_to(REPO)
        print(f"  {label}: {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
