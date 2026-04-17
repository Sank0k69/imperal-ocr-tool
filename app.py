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

SETTINGS_COLLECTION = "ocr_tool"
SETTINGS_KEY = "settings"
HISTORY_COLLECTION = "ocr_history"

DEFAULT_SETTINGS = {
    "server_url": "https://mos.lexa-lox.xyz",
    "server_api_key": "",
    "default_language": "auto",
    "preserve_layout": False,
    "save_history": True,
}


async def load_settings(ctx) -> dict:
    try:
        doc = await ctx.store.get(SETTINGS_COLLECTION, SETTINGS_KEY)
    except Exception:
        doc = None
    data = getattr(doc, "data", None) if doc else None
    if not isinstance(data, dict):
        data = {}
    return {**DEFAULT_SETTINGS, **data}


async def save_settings(ctx, values: dict) -> dict:
    current = await load_settings(ctx)
    merged = {**current, **{k: v for k, v in values.items() if v is not None}}
    try:
        doc = await ctx.store.get(SETTINGS_COLLECTION, SETTINGS_KEY)
    except Exception:
        doc = None
    if doc:
        await ctx.store.update(SETTINGS_COLLECTION, SETTINGS_KEY, merged)
    else:
        set_fn = getattr(ctx.store, "set", None)
        if callable(set_fn):
            await set_fn(f"{SETTINGS_COLLECTION}/{SETTINGS_KEY}", merged)
        else:
            await ctx.store.update(SETTINGS_COLLECTION, SETTINGS_KEY, merged)
    return merged


def server_ready(s: dict) -> bool:
    return bool(s.get("server_url") and s.get("server_api_key"))
