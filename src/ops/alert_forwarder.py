from __future__ import annotations

import json
import os

import httpx
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

app = FastAPI()


@app.post("/alert")
async def forward_alert(req: Request):
    payload = await req.json()
    text = f"*GMNAP Alert*\n```{json.dumps(payload, ensure_ascii=False, indent=2)}```"
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        return JSONResponse({"status": "no_webhook_configured"}, status_code=202)
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.post(url, json={"text": text})
        r.raise_for_status()
    return {"status": "ok"}
