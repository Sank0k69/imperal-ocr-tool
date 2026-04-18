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
        return ui.Stack(children=[
            ui.Header(text="OCR Tool", level=4),
            ui.Alert(message="Server not configured", type="warning"),
            ui.Text(content="Open Settings panel →", variant="caption"),
        ])

    return ui.Stack(children=[
        ui.Header(text="OCR Tool", level=4),
        ui.Text(
            content=(s.get("server_url", "").replace("https://", "")[:32]) or "server",
            variant="caption",
        ),
        ui.Divider(),
        ui.Button(label="New Extraction", icon="Plus", variant="primary",
                  full_width=True, on_click=ui.Call("__panel__workspace")),
        ui.Button(label="History", icon="Clock", variant="secondary",
                  full_width=True, on_click=ui.Call("history", limit=20)),
        ui.Divider(),
        ui.Text(
            content="Ask Webbee: 'extract text from this image' and attach a file.",
            variant="caption",
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
    """Right-side settings. Inputs are DIRECT children of ui.Form — wrapping
    them in Stacks would drop the values from the submit payload."""
    s = await load_settings(ctx)

    status = ui.Badge(
        label=("Server ✓" if server_ready(s) else "Server ✗"),
        color=("green" if server_ready(s) else "red"),
    )

    form = ui.Form(
        action="save_settings",
        submit_label="Save",
        children=[
            ui.Header(text="Server", level=5),
            ui.Input(
                placeholder="Server URL — https://mos.lexa-lox.xyz",
                value=s.get("server_url", ""),
                param_name="server_url",
            ),
            ui.Input(
                placeholder=(
                    f"Server API Key — current {_masked(s.get('server_api_key', ''))}"
                    if s.get("server_api_key")
                    else "Server API Key — paste from VPS .env"
                ),
                value="",
                param_name="server_api_key",
            ),

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

    return ui.Stack(children=[
        ui.Header(text="Settings", level=3),
        status,
        ui.Divider(),
        form,
    ])
