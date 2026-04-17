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
    data = cfg if cfg is not None else {
        "server_url": "https://mos.test",
        "server_api_key": "k",
        "default_language": "eng",
        "save_history": True,
    }
    ctx.store._data.setdefault("ocr_tool", {})["settings"] = data
    return ctx


@pytest.mark.asyncio
async def test_extract_success(monkeypatch):
    async def fake_call(ctx, endpoint, payload=None):
        assert endpoint == "/api/ocr/extract"
        return {"text": "Hello", "language": "eng", "word_count": 1}
    monkeypatch.setattr(handlers, "call_mos", fake_call)

    result = await handlers.fn_extract(_ctx(), ExtractParams(image_b64="abc"))
    assert result.status == "success"
    assert result.data["text"] == "Hello"
    # History should have been recorded
    hist = await app_module.load_settings(_ctx())  # just exercise load path


@pytest.mark.asyncio
async def test_extract_no_image():
    result = await handlers.fn_extract(_ctx(), ExtractParams(image_b64=""))
    assert result.status == "error"


@pytest.mark.asyncio
async def test_extract_server_missing(monkeypatch):
    async def fake_call(ctx, endpoint, payload=None):
        return {"error": "Server URL or API Key not set", "_config": True}
    monkeypatch.setattr(handlers, "call_mos", fake_call)

    result = await handlers.fn_extract(_ctx({}), ExtractParams(image_b64="abc"))
    assert result.status == "error"
    assert "Server" in result.error


@pytest.mark.asyncio
async def test_history_returns_sorted(monkeypatch):
    ctx = _ctx()
    # seed store
    ctx.store._data.setdefault("ocr_history", {})
    ctx.store._data["ocr_history"]["a"] = {"text": "old", "word_count": 1, "timestamp": 100}
    ctx.store._data["ocr_history"]["b"] = {"text": "new", "word_count": 2, "timestamp": 200}

    result = await handlers.fn_history(ctx, HistoryQueryParams(limit=5))
    assert result.status == "success"
    assert result.data["count"] == 2
    assert result.data["items"][0]["text"] == "new"  # newest first


@pytest.mark.asyncio
async def test_save_settings_persists():
    ctx = _ctx({})
    params = SaveSettingsParams(
        server_url="https://mos.lexa-lox.xyz",
        server_api_key="new-key",
        default_language="rus",
    )
    result = await handlers.fn_save_settings(ctx, params)
    assert result.status == "success"
    s = await app_module.load_settings(ctx)
    assert s["server_url"] == "https://mos.lexa-lox.xyz"
    assert s["default_language"] == "rus"
