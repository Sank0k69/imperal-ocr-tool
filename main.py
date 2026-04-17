"""OCR Tool extension · entry point with module hot-reload."""
import sys
import os

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)

for _m in list(sys.modules):
    if _m in ("app", "api_client", "params", "handlers", "panels_main", "panels_side"):
        del sys.modules[_m]

from app import ext, chat  # noqa: E402, F401

import handlers       # noqa: E402, F401
import panels_main    # noqa: E402, F401
import panels_side    # noqa: E402, F401


@ext.on_install
async def on_install(ctx):
    from imperal_sdk.types import ActionResult
    return ActionResult.success(
        summary="OCR Tool installed. Open Settings and paste your server URL + API key.",
    )


@ext.health_check
async def health(ctx):
    from imperal_sdk.types import ActionResult
    from app import load_settings, server_ready
    s = await load_settings(ctx)
    return ActionResult.success(data={
        "version": "2.0.0",
        "server_configured": server_ready(s),
    })
