# Imperal OCR Tool

Extract text from any image. Runs locally on our server (Tesseract 5), no AI tokens spent.

## What it does

- **Central workspace** — drop an image, get text back with word count + detected language.
- **History tab** — past extractions, searchable, one click to re-use.
- **Quick actions** — Screenshot / Receipt / Document-with-layout presets.
- **IPC** — `ctx.extensions.call("ocr-tool", "extract", image_b64=..., language="auto")` for other extensions.

## How it works

```
User drops image
       │
       ▼
[ ocr-tool extension ] (Imperal Cloud)
       │  HTTPS + X-API-Key (per-user, stored encrypted in ctx.store)
       ▼
[ mos.lexa-lox.xyz ]   ← our FastAPI server
       │  POST /api/ocr/extract  (base64 bytes in, text out)
       ▼
[ Tesseract 5.3 ]      ← local, 6 languages (eng, rus, spa, deu, fra + osd)
       │
       ▼
  Text + word_count + layout
```

The extension never touches an LLM. All work is plain Python on our server. If the AI quota runs out, OCR keeps working.

## Install

1. Marketplace → OCR Tool → Install.
2. Settings panel (right) → paste:
   - **Server URL:** `https://mos.lexa-lox.xyz`
   - **Server API Key:** from our VPS `.env`
   - Default language, preserve-layout toggle, save-history toggle.
3. Upload any image in the workspace tab.

## Development

```bash
pip install -e .[dev]
imperal validate
pytest
```

### Files (all ≤ 300 lines)

```
main.py           hot-reload entry point
app.py            Extension + ChatExtension init; load_/save_settings
api_client.py     HTTP client → mos.lexa-lox.xyz
params.py         Pydantic models
handlers.py       chat functions (extract, history, save_settings) + IPC
panels_main.py    central workspace (slot="main")
panels_side.py    sidebar + settings Form
imperal.json      manifest
tests/            unit tests with MockContext
```

## License

AGPL-3.0.
