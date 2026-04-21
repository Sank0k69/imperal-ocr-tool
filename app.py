"""OCR Tool — extension init + settings + constants.

Server URL and API key are baked into the extension — they are NOT user
settings. The extension talks to one server (our infra); the user pays
via Imperal Actions (1 action per extraction), not by bringing their
own OCR backend. Only genuine user preferences (language, layout mode,
history toggle) live in the Settings tab.
"""
from imperal_sdk import Extension, ChatExtension

# Our Marketing OS server — baked in. Rotate in-code if the key leaks.
SERVER_URL = "https://mos.lexa-lox.xyz"
SERVER_API_KEY = "dd5f08814b30d05ff8b573231a14a6826c39d7c07f226995c9a8b1573ceebb90"

ext = Extension("ocr-tool", version="2.1.2")

chat = ChatExtension(
    ext,
    tool_name="ocr",
    description=(
        "Image-to-text extraction. Drop screenshots, photos, documents, "
        "receipts, handwritten notes — get accurate text back. "
        "Runs Tesseract on our server, 1 action per extraction."
    ),
    max_rounds=4,
)

SETTINGS_COLLECTION = "ocr_settings"
HISTORY_COLLECTION = "ocr_history"

DEFAULT_SETTINGS = {
    "default_language": "auto",
    "preserve_layout": False,
    "save_history": True,
    "last_result": "",
    "last_language": "",
    "last_words": 0,
}


async def load_settings(ctx) -> dict:
    """One doc per user; we find it via query(limit=1) — create() assigns
    server-side ids we can't override, so a fixed key won't work across
    SDK versions."""
    try:
        page = await ctx.store.query(SETTINGS_COLLECTION, limit=1)
    except Exception:
        return dict(DEFAULT_SETTINGS)
    docs = getattr(page, "data", None) or []
    if docs and isinstance(getattr(docs[0], "data", None), dict):
        return {**DEFAULT_SETTINGS, **docs[0].data}
    return dict(DEFAULT_SETTINGS)


async def save_settings(ctx, values: dict) -> dict:
    """Upsert the single settings doc."""
    current = await load_settings(ctx)
    merged = {**current, **{k: v for k, v in values.items() if v is not None}}
    page = await ctx.store.query(SETTINGS_COLLECTION, limit=1)
    docs = getattr(page, "data", None) or []
    if docs:
        await ctx.store.update(SETTINGS_COLLECTION, docs[0].id, merged)
    else:
        await ctx.store.create(SETTINGS_COLLECTION, merged)
    return merged
