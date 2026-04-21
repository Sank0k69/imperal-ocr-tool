"""Chat-function handlers for OCR Tool."""
# No `from __future__ import annotations` — V6 validator needs real annotations.

import time

from imperal_sdk.types import ActionResult

from app import chat, ext, load_settings, save_settings, HISTORY_COLLECTION
from api_client import call_mos
from params import ExtractParams, HistoryQueryParams, SaveSettingsParams


def _err(data: dict) -> ActionResult:
    return ActionResult.error(error=data.get("error", "unknown error"))


def _normalize_image(payload) -> str:
    """Extract the base64 string out of the various shapes that arrive from
    ui.FileUpload, direct strings, or IPC calls."""
    if payload is None:
        return ""
    if isinstance(payload, str):
        b64 = payload
    elif isinstance(payload, list) and payload:
        first = payload[0]
        b64 = first.get("data_base64", "") if isinstance(first, dict) else str(first)
    elif isinstance(payload, dict):
        b64 = payload.get("data_base64", "")
    else:
        b64 = ""
    # Browser FileReader may prefix data URIs — strip the prefix so tesseract
    # receives the raw base64 body.
    if b64.startswith("data:") and "," in b64:
        b64 = b64.split(",", 1)[1]
    return b64


@chat.function(
    "extract",
    description="Extract text from an image. Drop a file or pass base64.",
    action_type="write",
    event="ocr.extracted",
)
async def fn_extract(ctx, params: ExtractParams) -> ActionResult:
    """Run OCR on one image. The FileUpload payload, a bare base64 string,
    or an IPC dict all normalize to the same code path."""
    image_b64 = _normalize_image(params.image_b64)
    if not image_b64:
        return ActionResult.error(error="No image provided. Drop a file or paste base64.")

    s = await load_settings(ctx)
    language = params.language or s.get("default_language", "auto")
    preserve = params.preserve_layout or bool(s.get("preserve_layout", False))

    data = await call_mos(ctx, "/api/ocr/extract", {
        "image_b64": image_b64,
        "language": language,
        "preserve_layout": preserve,
    })
    if "error" in data:
        return _err(data)

    # Save to history + stash the last result so the workspace panel can
    # render it after its refresh fires on the ocr.extracted event.
    updates = {
        "last_result": data.get("text", "")[:20000],
        "last_language": data.get("language", language),
        "last_words": data.get("word_count", 0),
    }
    if s.get("save_history", True) and data.get("text"):
        try:
            await ctx.store.create(HISTORY_COLLECTION, {
                "text": data["text"][:2000],
                "word_count": data.get("word_count", 0),
                "language": data.get("language", language),
                "timestamp": time.time(),
            })
        except Exception:
            pass
    try:
        await save_settings(ctx, updates)
    except Exception:
        pass

    summary = f"Extracted {data.get('word_count', 0)} words ({data.get('language', language)})"
    return ActionResult.success(data=data, summary=summary)


@chat.function("history", description="Recent OCR extractions.", action_type="read")
async def fn_history(ctx, params: HistoryQueryParams) -> ActionResult:
    """Return the user's recent extractions."""
    page = await ctx.store.query(HISTORY_COLLECTION, limit=params.limit)
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
    description="Save OCR Tool preferences (language, layout, history toggle).",
    action_type="write",
    event="ocr.settings.saved",
)
async def fn_save_settings(ctx, params: SaveSettingsParams) -> ActionResult:
    """Only user-facing preferences. Server URL / API key are baked-in
    constants, not user-editable."""
    updates = {
        "default_language": params.default_language,
        "preserve_layout": bool(params.preserve_layout),
        "save_history": bool(params.save_history),
    }
    await save_settings(ctx, updates)
    return ActionResult.success(data=updates, summary="Preferences saved")


# ─── IPC for other extensions ─────────────────────────────

@ext.expose("extract")
async def ipc_extract(ctx, image_b64: str = "", language: str = "auto",
                      preserve_layout: bool = False) -> ActionResult:
    """IPC: extract text from a base64 image."""
    data = await call_mos(ctx, "/api/ocr/extract", {
        "image_b64": _normalize_image(image_b64),
        "language": language,
        "preserve_layout": preserve_layout,
    })
    if "error" in data:
        return _err(data)
    return ActionResult.success(data=data)
