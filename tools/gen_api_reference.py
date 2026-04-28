#!/usr/bin/env python3
"""Generate API reference docs from the FastAPI app's OpenAPI schema.

Tier-3 audit item 3.1: external evaluators want to see the API
surface without spinning up the server. FastAPI auto-generates an
OpenAPI schema at ``/openapi.json`` (and a Swagger UI at ``/docs``)
when the server runs, but neither is committed. This script:

1. Imports ``create_app()`` and pulls the OpenAPI schema out via
   ``app.openapi()``.
2. Writes it verbatim to ``docs/openapi.json`` (machine-readable;
   pipe into Postman, openapi-generator, etc.).
3. Renders a human-readable markdown summary to ``docs/api_reference.md``
   covering each path / method / parameters / responses.

Idempotent. Re-run after any endpoint change to keep the docs in
sync. Wired into the Makefile as ``make api-docs``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parent.parent
OUT_JSON = REPO / "docs" / "openapi.json"
OUT_MD = REPO / "docs" / "api_reference.md"


def _gather_schema() -> Dict[str, Any]:
    sys.path.insert(0, str(REPO))
    from src.api.server import create_app

    app = create_app()
    return app.openapi()


def _format_param(p: Dict[str, Any]) -> str:
    name = p.get("name", "?")
    where = p.get("in", "?")
    required = " **(required)**" if p.get("required") else ""
    schema = p.get("schema") or {}
    typ = schema.get("type", "any")
    desc = (p.get("description") or "").strip()
    line = f"  - `{name}` (`{typ}`, {where}){required}"
    if desc:
        line += f" — {desc}"
    return line


def _format_response(code: str, body: Dict[str, Any]) -> str:
    desc = (body.get("description") or "").strip()
    content = body.get("content") or {}
    media_types = ", ".join(sorted(content.keys())) if content else "—"
    return f"  - `{code}` ({media_types}){' — ' + desc if desc else ''}"


def _format_endpoint(path: str, method: str, op: Dict[str, Any]) -> List[str]:
    lines = [f"### `{method.upper()} {path}`", ""]
    summary = (op.get("summary") or op.get("operationId") or "").strip()
    if summary:
        lines.append(f"**{summary}**")
        lines.append("")
    desc = (op.get("description") or "").strip()
    if desc:
        lines.append(desc)
        lines.append("")
    params = op.get("parameters") or []
    if params:
        lines.append("**Parameters:**")
        lines.extend(_format_param(p) for p in params)
        lines.append("")
    body = op.get("requestBody") or {}
    if body:
        content = body.get("content") or {}
        for mt, mb in content.items():
            schema = mb.get("schema") or {}
            sname = schema.get("$ref", "").split("/")[-1] or schema.get(
                "type", "object"
            )
            lines.append(f"**Request body** (`{mt}`): `{sname}`")
        lines.append("")
    responses = op.get("responses") or {}
    if responses:
        lines.append("**Responses:**")
        for code in sorted(responses):
            lines.append(_format_response(code, responses[code]))
        lines.append("")
    return lines


def _render_markdown(schema: Dict[str, Any]) -> str:
    info = schema.get("info") or {}
    title = info.get("title", "GMNAP API")
    version = info.get("version", "")
    paths = schema.get("paths") or {}

    lines = [
        f"# {title} reference",
        "",
        "Auto-generated from the FastAPI OpenAPI schema by",
        f"`tools/gen_api_reference.py`. Version: **{version}**.",
        "",
        f"Endpoints: **{len(paths)}**. Re-generate after any endpoint",
        "change with `make api-docs`. The full machine-readable schema",
        "is at `docs/openapi.json`.",
        "",
        "## Endpoints",
        "",
    ]

    for path in sorted(paths):
        methods = paths[path]
        for method in ("get", "post", "put", "patch", "delete"):
            if method in methods:
                lines.extend(_format_endpoint(path, method, methods[method]))

    schemas = (schema.get("components") or {}).get("schemas") or {}
    if schemas:
        lines += [
            "## Component schemas",
            "",
            "Pydantic models referenced by the endpoints above.",
            "Property-level detail lives in the underlying class docstrings",
            "in `src/api/server.py` — this section just lists which models",
            "exist so reviewers can grep for them.",
            "",
            "| Schema | Properties |",
            "|---|---|",
        ]
        for name in sorted(schemas):
            props = (schemas[name].get("properties") or {}).keys()
            lines.append(f"| `{name}` | {', '.join(f'`{p}`' for p in props) or '—'} |")
        lines.append("")

    lines += [
        "## Cross-cutting middleware (not in the schema)",
        "",
        "These behaviours are enforced by FastAPI middleware in",
        "`src/api/server.py` and aren't part of the OpenAPI surface:",
        "",
        "- **Rate limiting**: 60 req/min for free tier (configurable",
        "  via `GMNAP_FREE_RPM`); 10 000/min for paid Bearer-token tier",
        "  (configurable via `GMNAP_PAID_RPM`). Tokens listed in",
        "  `GMNAP_API_TOKENS` (comma-separated) skip the free gate.",
        "- **Hashcash proof-of-work**: free tier requires an 18-bit",
        "  SHA-256 stamp in the `X-Hashcash` header (~1 s on a modern CPU).",
        "  See `static/app.js:generateHashcash` for the browser miner.",
        "- **Security headers**: CSP `default-src 'self'; script-src 'self';",
        "  style-src 'self'`, HSTS, X-Frame-Options DENY, etc.",
        "- **Prometheus metrics**: every request records latency + status",
        "  on `gmnap_api_request_duration_seconds` /",
        "  `gmnap_api_requests_total`. Scraped from `/metrics`.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "make api-docs",
        "# or:  PYTHONPATH=. python3 tools/gen_api_reference.py",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    schema = _gather_schema()

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(schema, indent=2, sort_keys=True), encoding="utf-8")
    OUT_MD.write_text(_render_markdown(schema), encoding="utf-8")

    paths = schema.get("paths") or {}
    print(f"Documented {len(paths)} endpoint paths")
    print(f"  wrote {OUT_JSON.relative_to(REPO)}")
    print(f"  wrote {OUT_MD.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
