"""Unit tests with MockContext. No network — monkey-patch call_mos."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from imperal_sdk.testing import MockContext

import handlers
import app as app_module
from params import ExtractParams, HistoryQueryParams, SaveSettingsParams


def _ctx(cfg: dict | None = None) -> MockContext:
    ctx = MockContext(role="user")
    data = cfg if cfg is not None else {"default_language": "eng", "save_history": True}
    if data:
        ctx.store._data.setdefault("ocr_settings", {})["seed"] = data
    return ctx


@pytest.mark.asyncio
async def test_extract_success_with_string(monkeypatch):
    async def fake_call(ctx, endpoint, payload=None):
        assert endpoint == "/api/ocr/extract"
        assert payload["image_b64"] == "abc"
        return {"text": "Hello", "language": "eng", "word_count": 1}
    monkeypatch.setattr(handlers, "call_mos", fake_call)

    result = await handlers.fn_extract(_ctx(), ExtractParams(image_b64="abc"))
    assert result.status == "success"
    assert result.data["text"] == "Hello"


@pytest.mark.asyncio
async def test_extract_accepts_fileupload_list(monkeypatch):
    """FileUpload sends list[dict] — handler must unwrap it."""
    captured = {}

    async def fake_call(ctx, endpoint, payload=None):
        captured["payload"] = payload
        return {"text": "OK", "language": "eng", "word_count": 1}
    monkeypatch.setattr(handlers, "call_mos", fake_call)

    upload = [{"data_base64": "iVBORw0KGgo", "name": "x.png", "size": 123}]
    result = await handlers.fn_extract(_ctx(), ExtractParams(image_b64=upload))
    assert result.status == "success"
    assert captured["payload"]["image_b64"] == "iVBORw0KGgo"


@pytest.mark.asyncio
async def test_extract_strips_data_uri_prefix(monkeypatch):
    """Browsers prefix FileReader output with data:image/png;base64,… — strip it."""
    captured = {}

    async def fake_call(ctx, endpoint, payload=None):
        captured["payload"] = payload
        return {"text": "OK", "language": "eng", "word_count": 1}
    monkeypatch.setattr(handlers, "call_mos", fake_call)

    result = await handlers.fn_extract(
        _ctx(),
        ExtractParams(image_b64="data:image/png;base64,iVBORw0KGgo"),
    )
    assert result.status == "success"
    assert captured["payload"]["image_b64"] == "iVBORw0KGgo"


@pytest.mark.asyncio
async def test_extract_no_image():
    result = await handlers.fn_extract(_ctx(), ExtractParams(image_b64=""))
    assert result.status == "error"


@pytest.mark.asyncio
async def test_history_returns_sorted():
    ctx = _ctx()
    ctx.store._data.setdefault("ocr_history", {})
    ctx.store._data["ocr_history"]["a"] = {"text": "old", "word_count": 1, "timestamp": 100}
    ctx.store._data["ocr_history"]["b"] = {"text": "new", "word_count": 2, "timestamp": 200}

    result = await handlers.fn_history(ctx, HistoryQueryParams(limit=5))
    assert result.status == "success"
    assert result.data["count"] == 2
    assert result.data["items"][0]["text"] == "new"


@pytest.mark.asyncio
async def test_save_settings_persists():
    ctx = _ctx({})
    params = SaveSettingsParams(default_language="rus", preserve_layout=True, save_history=False)
    result = await handlers.fn_save_settings(ctx, params)
    assert result.status == "success"
    s = await app_module.load_settings(ctx)
    assert s["default_language"] == "rus"
    assert s["preserve_layout"] is True
    assert s["save_history"] is False
