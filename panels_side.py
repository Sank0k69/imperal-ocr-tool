"""Left sidebar (stats + recent) and right workspace (drop-zone-first UI)."""
from __future__ import annotations

from imperal_sdk import ui

from app import ext, load_settings, HISTORY_COLLECTION


LANG_OPTIONS = [
    {"value": "auto", "label": "Auto-detect (EN + RU)"},
    {"value": "eng", "label": "English"},
    {"value": "rus", "label": "Russian"},
    {"value": "spa", "label": "Spanish"},
    {"value": "deu", "label": "German"},
    {"value": "fra", "label": "French"},
]


# ───────────────────── Left sidebar ──────────────────────

@ext.panel("sidebar", slot="left", title="OCR Tool", icon="Scan",
           default_width=220,
           refresh="on_event:ocr.extracted")
async def sidebar_panel(ctx):
    s = await load_settings(ctx)

    # Stats
    try:
        page = await ctx.store.query(HISTORY_COLLECTION, limit=200)
        docs = getattr(page, "data", []) or []
        count = len(docs)
        words = sum(int(d.data.get("word_count", 0) or 0) for d in docs)
    except Exception:
        count, words = 0, 0

    return ui.Stack(children=[
        ui.Header(text="OCR Tool", level=4),
        ui.Text(content="Tesseract. 1 action per extraction.", variant="caption"),
        ui.Divider(),
        ui.Stats(children=[
            ui.Stat(label="Extractions", value=str(count), color="blue"),
            ui.Stat(label="Total words", value=str(words), color="violet"),
        ]),
        ui.Divider(),
        ui.Text(content="Default language", variant="caption"),
        ui.Text(content=(s.get("default_language", "auto") or "auto").upper()),
        ui.Divider(),
        ui.Text(
            content="Drop an image into the main panel or ask Webbee: 'extract text from this image'.",
            variant="caption",
        ),
    ])


# ─────────────── Right workspace (tabs) ────────────────

def _drop_zone(s: dict) -> ui.UINode:
    # FileUpload auto-injects the file's base64 into the on_upload Call under
    # param_name. Do NOT pass image_b64 explicitly — "$value" is not a
    # recognized template, it would arrive as the literal string.
    return ui.FileUpload(
        accept="image/*",
        max_size_mb=10,
        max_files=1,
        on_upload=ui.Call("extract",
                          language=s.get("default_language", "auto"),
                          preserve_layout=bool(s.get("preserve_layout", False))),
        param_name="image_b64",
    )


def _result_card(s: dict) -> ui.UINode:
    text = s.get("last_result", "") or ""
    lang = s.get("last_language", "") or ""
    words = s.get("last_words", 0) or 0
    if not text:
        return ui.Empty(
            message="Drop an image above to see the extracted text here.",
            icon="FileText",
        )
    return ui.Stack(children=[
        ui.Stack(children=[
            ui.Badge(label=lang.upper() if lang else "—", color="blue"),
            ui.Badge(label=f"{words} words", color="violet"),
        ], direction="horizontal"),
        ui.Code(code=text, language="text"),
        ui.Text(content="Select the text in the box above and copy it.",
                variant="caption"),
    ])


def _history_list(items: list[dict]) -> ui.UINode:
    if not items:
        return ui.Empty(message="No extractions yet.", icon="Clock")
    list_items = []
    for h in items[:50]:
        list_items.append(ui.ListItem(
            id=str(h.get("timestamp", 0)),
            title=f"{h.get('word_count', 0)} words",
            subtitle=(h.get("text", "") or "")[:120],
            meta=h.get("language", ""),
            icon="FileText",
            badge=ui.Badge(label=h.get("language", "—"), color="blue"),
        ))
    return ui.List(items=list_items, searchable=True)


def _preferences_form(s: dict) -> ui.UINode:
    return ui.Form(
        action="save_settings",
        submit_label="Save preferences",
        children=[
            ui.Header(text="Defaults", level=5),
            ui.Select(
                param_name="default_language",
                options=LANG_OPTIONS,
                value=s.get("default_language", "auto"),
                placeholder="Default language",
            ),
            ui.Toggle(
                param_name="preserve_layout",
                label="Preserve document layout (columns/tables)",
                value=bool(s.get("preserve_layout", False)),
            ),
            ui.Toggle(
                param_name="save_history",
                label="Save extractions to history",
                value=bool(s.get("save_history", True)),
            ),
        ],
    )


@ext.panel("workspace", slot="right", title="OCR Tool", icon="Scan",
           default_width=540,
           refresh="on_event:ocr.extracted")
async def workspace_panel(ctx):
    s = await load_settings(ctx)

    try:
        page = await ctx.store.query(HISTORY_COLLECTION, limit=50)
        docs = getattr(page, "data", []) or []
        items = sorted([d.data for d in docs],
                       key=lambda x: x.get("timestamp", 0), reverse=True)
    except Exception:
        items = []

    return ui.Stack(children=[
        ui.Header(text="OCR Tool", level=3),
        ui.Text(
            content="Tesseract 5 — English, Russian, Spanish, German, French. 1 action per extraction.",
            variant="caption",
        ),
        ui.Section(title="Drop an image", children=[_drop_zone(s)]),
        ui.Section(title="Result", children=[_result_card(s)]),
        ui.Section(title=f"History ({len(items)})", collapsible=True,
                   children=[_history_list(items)]),
        ui.Section(title="Preferences", collapsible=True,
                   children=[_preferences_form(s)]),
    ])
