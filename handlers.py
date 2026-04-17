"""Chat-function handlers for OCR Tool."""
# No `from __future__ import annotations` — V6 validator needs real annotations.

import time

from imperal_sdk.types import ActionResult

from app import chat, ext, load_settings, save_settings, HISTORY_COLLECTION
from api_client import call_mos
from params import ExtractParams, HistoryQueryParams, SaveSettingsParams


def _err(data: dict) -> ActionResult:
    return ActionResult.error(error=data.get("error", "unknown error"))


@chat.function(
    "extract",
    description="Extract text from an image. Pass raw base64 (no data: prefix).",
    action_type="write",
    event="ocr.extracted",
)
async def fn_extract(ctx, params: ExtractParams) -> ActionResult:
    """Send base64 image bytes to our server's Tesseract pipeline."""
    if not params.image_b64:
        return ActionResult.error(error="Upload an image first.")

    s = await load_settings(ctx)
    language = params.language or s.get("default_language", "auto")
    preserve = params.preserve_layout or bool(s.get("preserve_layout", False))

    data = await call_mos(ctx, "/api/ocr/extract", {
        "image_b64": params.image_b64,
        "language": language,
        "preserve_layout": preserve,
    })
    if "error" in data:
        return _err(data)

    if s.get("save_history", True) and data.get("text"):
        try:
            await ctx.store.create(HISTORY_COLLECTION, {
                "text": data["text"][:2000],  # cap for storage
                "word_count": data.get("word_count", 0),
                "language": data.get("language", language),
                "timestamp": time.time(),
            })
        except Exception:
            pass  # history is best-effort

    summary = f"{data.get('word_count', 0)} words in {data.get('language', language)}"
    return ActionResult.success(data=data, summary=summary)


@chat.function(
    "history",
    description="Return the user's recent OCR extractions.",
    action_type="read",
)
async def fn_history(ctx, params: HistoryQueryParams) -> ActionResult:
    """Read recent extractions from the per-user store."""
    page = await ctx.store.query(HISTORY_COLLECTION, where={}, limit=params.limit)
    docs = getattr(page, "data", []) if page is not None else []
    items = sorted(
        [d.data for d in docs],
        key=lambda x: x.get("timestamp", 0),
        reverse=True,
    )[: params.limit]
    return ActionResult.success(
        data={"items": items, "count": len(items)},
        summary=f"{len(items)} extraction(s)",
    )


@chat.function(
    "save_settings",
    description="Save OCR Tool settings (server creds + default language).",
    action_type="write",
    event="ocr.settings.saved",
)
async def fn_save_settings(ctx, params: SaveSettingsParams) -> ActionResult:
    """Persist settings. Blank fields keep current values (except bool flags)."""
    updates: dict = {}
    if params.server_url:
        updates["server_url"] = params.server_url.strip()
    if params.server_api_key:
        updates["server_api_key"] = params.server_api_key.strip()
    if params.default_language:
        updates["default_language"] = params.default_language.strip()
    # Bools always persist (they have well-defined false defaults)
    updates["preserve_layout"] = bool(params.preserve_layout)
    updates["save_history"] = bool(params.save_history)

    await save_settings(ctx, updates)
    return ActionResult.success(
        data={"saved_keys": list(updates.keys())},
        summary="Settings saved",
    )


# IPC — callable by other extensions (e.g. content-pipeline scanning receipts)


@ext.expose("extract")
async def ipc_extract(ctx, image_b64: str = "", language: str = "auto",
                      preserve_layout: bool = False) -> ActionResult:
    """IPC: extract text from a base64 image."""
    data = await call_mos(ctx, "/api/ocr/extract", {
        "image_b64": image_b64,
        "language": language,
        "preserve_layout": preserve_layout,
    })
    if "error" in data:
        return _err(data)
    return ActionResult.success(data=data)
