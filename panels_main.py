"""Central workspace panel — drop image + see text."""
# `from __future__ import annotations` keeps type hints as strings so forward
# refs like ui.UINode don't need to resolve at import time. V6 only inspects
# @chat.function handlers (which live in handlers.py), so this is safe here.
from __future__ import annotations

from imperal_sdk import ui

from app import ext, load_settings, server_ready, HISTORY_COLLECTION


def _config_prompt() -> ui.UINode:
    return ui.Stack(children=[
        ui.Header(text="OCR Tool", level=3),
        ui.Alert(
            message="Configure the server URL and API key in Settings (right panel) first.",
            type="warning",
        ),
    ])


def _upload_card(s: dict) -> ui.UINode:
    return ui.Section(title="Upload an image", children=[
        ui.FileUpload(
            accept="image/*",
            max_size_mb=10,
            max_files=1,
            on_upload=ui.Call(
                "extract",
                image_b64="$value",
                language=s.get("default_language", "auto"),
            ),
            param_name="image_b64",
        ),
        ui.Text(
            content=("Supported: PNG, JPG, WebP, TIFF. Languages installed on server: "
                     "English, Russian, Spanish, German, French."),
            variant="caption",
        ),
    ])


def _quick_actions() -> ui.UINode:
    return ui.Stack(children=[
        ui.Button(label="Screenshot OCR", icon="Monitor", variant="secondary",
                  on_click=ui.Send(message="Extract text from my screenshot")),
        ui.Button(label="Receipt / Invoice", icon="Receipt", variant="secondary",
                  on_click=ui.Send(message="Extract structured data from a receipt")),
        ui.Button(label="Document (preserve layout)", icon="FileText", variant="secondary",
                  on_click=ui.Send(message="Extract text from a document, keep columns/tables")),
    ], direction="horizontal")


def _history_list(items: list[dict]) -> ui.UINode:
    if not items:
        return ui.Empty(message="No extractions yet — upload an image to begin", icon="Scan")

    list_items = []
    for h in items[:20]:
        list_items.append(ui.ListItem(
            id=str(h.get("timestamp", 0)),
            title=f"{h.get('word_count', 0)} words",
            subtitle=(h.get("text", "") or "")[:80],
            meta=h.get("language", ""),
            icon="FileText",
            badge=ui.Badge(label=h.get("language", "—"), color="blue"),
        ))
    return ui.List(items=list_items, searchable=True)


@ext.panel("workspace", slot="main", title="OCR Tool", icon="Scan",
           refresh="on_event:ocr.extracted,ocr.settings.saved")
async def workspace_panel(ctx):
    """Central workspace: upload + recent history."""
    s = await load_settings(ctx)
    if not server_ready(s):
        return _config_prompt()

    page = await ctx.store.query(HISTORY_COLLECTION, where={}, limit=50)
    docs = getattr(page, "data", []) if page is not None else []
    items = sorted(
        [d.data for d in docs],
        key=lambda x: x.get("timestamp", 0),
        reverse=True,
    )
    word_total = sum(i.get("word_count", 0) for i in items)

    stats = ui.Stats(children=[
        ui.Stat(label="Extractions", value=str(len(items)), color="blue"),
        ui.Stat(label="Total words", value=str(word_total), color="violet"),
        ui.Stat(label="Server", value="OK" if server_ready(s) else "—",
                color="green" if server_ready(s) else "gray"),
    ])

    tabs = ui.Tabs(tabs=[
        {"label": "Extract", "content": ui.Stack(children=[
            _upload_card(s),
            ui.Divider(),
            _quick_actions(),
        ])},
        {"label": f"History ({len(items)})", "content": _history_list(items)},
    ], default_tab=0)

    return ui.Stack(children=[
        ui.Header(text="OCR Tool", level=2),
        ui.Text(content="Tesseract on our server. No AI tokens.", variant="caption"),
        ui.Divider(),
        stats,
        ui.Divider(),
        tabs,
    ])
