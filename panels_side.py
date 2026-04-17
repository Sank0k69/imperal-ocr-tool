"""Left sidebar + right Settings panel."""
from __future__ import annotations

from imperal_sdk import ui

from app import ext, load_settings, server_ready

LANG_OPTIONS = [
    {"value": "auto", "label": "Auto (EN + RU)"},
    {"value": "eng", "label": "English"},
    {"value": "rus", "label": "Russian"},
    {"value": "spa", "label": "Spanish"},
    {"value": "deu", "label": "German"},
    {"value": "fra", "label": "French"},
]


@ext.panel("sidebar", slot="left", title="OCR Tool", icon="Scan",
           default_width=220)
async def sidebar_panel(ctx):
    s = await load_settings(ctx)

    if not server_ready(s):
        return ui.Stack([
            ui.Header("OCR Tool", level=4),
            ui.Alert("Server not configured", variant="warning"),
            ui.Text("Open Settings panel →", variant="muted"),
        ])

    return ui.Stack([
        ui.Header("OCR Tool", level=4),
        ui.Text(
            (s.get("server_url", "").replace("https://", "")[:32]) or "server",
            variant="muted", size="sm",
        ),
        ui.Divider(),
        ui.Button("New Extraction", icon="Plus", variant="primary", full_width=True,
                  on_click=ui.Call("__panel__workspace")),
        ui.Button("History", icon="Clock", variant="secondary", full_width=True,
                  on_click=ui.Call("history", limit=20)),
        ui.Divider(),
        ui.Text(
            "Ask Webbee: 'extract text from this image' and attach a file.",
            variant="muted", size="sm",
        ),
    ])


def _masked(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "••••"
    return "••••" + value[-4:]


@ext.panel("settings", slot="right", title="Settings", icon="Settings",
           default_width=300, refresh="on_event:ocr.settings.saved")
async def settings_panel(ctx):
    s = await load_settings(ctx)

    status = ui.Badge("Server ✓", color="green") if server_ready(s) else ui.Badge("Server ✗", color="red")

    form = ui.Form(
        action="save_settings",
        submit_label="Save",
        children=[
            ui.Header("Server", level=5),
            ui.Input(name="server_url", label="Server URL",
                     value=s.get("server_url", ""),
                     placeholder="https://mos.lexa-lox.xyz"),
            ui.Input(name="server_api_key", label="Server API Key",
                     type="password",
                     placeholder=_masked(s.get("server_api_key", "")) or "paste from VPS .env"),

            ui.Divider(),
            ui.Header("Defaults", level=5),
            ui.Select(
                name="default_language",
                label="Default language",
                options=LANG_OPTIONS,
                value=s.get("default_language", "auto"),
            ),
            ui.Toggle(
                name="preserve_layout",
                label="Preserve document layout (columns/tables)",
                value=bool(s.get("preserve_layout", False)),
            ),
            ui.Toggle(
                name="save_history",
                label="Save extractions to history",
                value=bool(s.get("save_history", True)),
            ),
        ],
    )

    return ui.Stack([
        ui.Header("Settings", level=3),
        status,
        ui.Divider(),
        form,
    ])
