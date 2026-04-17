"""HTTP client — calls our Marketing OS server OCR endpoints."""
from app import load_settings, server_ready

TIMEOUT = 60  # Tesseract on large images can take a bit


async def call_mos(ctx, endpoint: str, payload: dict | None = None) -> dict:
    """POST to server. Returns dict; `{"error": ..., "_config": True}` on missing creds."""
    s = await load_settings(ctx)
    if not server_ready(s):
        return {"error": "Server URL or API Key not set", "_config": True}

    resp = await ctx.http.post(
        f"{s['server_url'].rstrip('/')}{endpoint}",
        json=payload or {},
        headers={"X-API-Key": s["server_api_key"]},
        timeout=TIMEOUT,
    )
    if not resp.ok:
        return {"error": f"server {resp.status_code}: {(resp.text or '')[:200]}"}
    return resp.json()


async def fetch_languages(ctx) -> list[str]:
    """List OCR languages installed on the server. GET /api/ocr/languages."""
    s = await load_settings(ctx)
    if not server_ready(s):
        return []
    resp = await ctx.http.get(
        f"{s['server_url'].rstrip('/')}/api/ocr/languages",
        headers={"X-API-Key": s["server_api_key"]},
        timeout=10,
    )
    if not resp.ok:
        return []
    body = resp.json()
    return body.get("languages") or []
