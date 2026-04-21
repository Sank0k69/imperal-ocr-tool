"""OCR Tool extension · entry point with module hot-reload."""
import sys
import os

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)

for _m in list(sys.modules):
    if _m in ("app", "api_client", "params", "handlers", "panels_side"):
        del sys.modules[_m]

from app import ext, chat  # noqa: E402, F401

import handlers       # noqa: E402, F401
import panels_side    # noqa: E402, F401


@ext.on_install
async def on_install(ctx):
    from imperal_sdk.types import ActionResult
    return ActionResult.success(
        summary="OCR Tool installed. Drop an image to extract text — 1 action per extraction.",
    )


@ext.health_check
async def health(ctx):
    from imperal_sdk.types import ActionResult
    return ActionResult.success(data={"version": "2.1.3"})
