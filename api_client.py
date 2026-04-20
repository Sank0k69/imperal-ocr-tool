"""HTTP client — calls our Marketing OS server OCR endpoints. No user creds needed."""
from app import SERVER_URL, SERVER_API_KEY

TIMEOUT = 60  # Tesseract on large images can take a bit


async def call_mos(ctx, endpoint: str, payload: dict | None = None) -> dict:
    """POST to our server. Auth is a bundled static key — this is an invariant
    of the extension, not a user setting."""
    resp = await ctx.http.post(
        f"{SERVER_URL.rstrip('/')}{endpoint}",
        json=payload or {},
        headers={"X-API-Key": SERVER_API_KEY},
        timeout=TIMEOUT,
    )
    if not resp.ok:
        try:
            body = resp.text()[:200]
        except Exception:
            body = ""
        return {"error": f"server {resp.status_code}: {body}"}
    return resp.json()
