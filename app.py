"""OCR Tool — extension init + settings helpers.

Thin-client: the extension sends base64 image bytes to our server
(``/api/ocr/extract``), which runs Tesseract locally and returns text.
No AI tokens are burned here.
"""
from imperal_sdk import Extension, ChatExtension

ext = Extension("ocr-tool", version="2.0.0")

chat = ChatExtension(
    ext,
    tool_name="ocr",
    description=(
        "Image-to-text extraction. Paste or upload a screenshot / photo / document — "
        "get the text back. Runs Tesseract on our server, no AI quota spent."
    ),
    max_rounds=4,
)

SETTINGS_COLLECTION = "ocr_settings"
HISTORY_COLLECTION = "ocr_history"

DEFAULT_SETTINGS = {
    "server_url": "https://mos.lexa-lox.xyz",
    "server_api_key": "",
    "default_language": "auto",
    "preserve_layout": False,
    "save_history": True,
}


async def load_settings(ctx) -> dict:
    """One doc per user — find it via query rather than a fixed key.
    ``ctx.store.create`` assigns a server-side id we cannot override, so
    using a known key with ``ctx.store.get`` is unreliable across save cycles."""
    try:
        page = await ctx.store.query(SETTINGS_COLLECTION, limit=1)
    except Exception:
        return dict(DEFAULT_SETTINGS)
    docs = getattr(page, "data", None) or []
    if docs and isinstance(getattr(docs[0], "data", None), dict):
        return {**DEFAULT_SETTINGS, **docs[0].data}
    return dict(DEFAULT_SETTINGS)


async def save_settings(ctx, values: dict) -> dict:
    """Upsert the settings doc (one per user, baseline SDK ops only)."""
    current = await load_settings(ctx)
    merged = {**current, **{k: v for k, v in values.items() if v is not None}}

    page = await ctx.store.query(SETTINGS_COLLECTION, limit=1)
    docs = getattr(page, "data", None) or []
    if docs:
        await ctx.store.update(SETTINGS_COLLECTION, docs[0].id, merged)
    else:
        await ctx.store.create(SETTINGS_COLLECTION, merged)
    return merged


def server_ready(s: dict) -> bool:
    return bool(s.get("server_url") and s.get("server_api_key"))
