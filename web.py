#!/usr/bin/env python3
"""OCR Tool — Standalone Web UI for local testing."""
import os, sys, json
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

load_dotenv(Path(__file__).parent.parent / "video-creator" / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent / "video-creator"))

app = FastAPI(title="OCR Tool")

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

@app.post("/api/extract")
async def extract(req: Request):
    body = await req.json()
    image_url = body.get("image_url", "")
    fmt = body.get("format", "plain")
    lang = body.get("language", "auto")
    instructions = body.get("instructions", "")
    
    if not image_url:
        return JSONResponse({"ok": False, "error": "No image URL"}, status_code=400)
    
    import httpx
    prompt = f"Extract ALL text from this image. Format: {fmt}."
    if lang != "auto":
        prompt += f" Language: {lang}."
    if instructions:
        prompt += f" {instructions}"
    
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post("https://api.anthropic.com/v1/messages", 
                headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 2048,
                    "messages": [{"role": "user", "content": [
                        {"type": "image", "source": {"type": "url", "url": image_url}},
                        {"type": "text", "text": prompt}
                    ]}]
                })
            data = resp.json()
            text = data.get("content", [{}])[0].get("text", "")
            return JSONResponse({"ok": True, "text": text, "words": len(text.split())})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload image file, convert to base64, extract text."""
    import base64, httpx
    content = await file.read()
    b64 = base64.standard_b64encode(content).decode()
    media_type = file.content_type or "image/png"

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 2048,
                    "messages": [{"role": "user", "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                        {"type": "text", "text": "Extract ALL text from this image accurately. Return only the text."}
                    ]}]
                })
            data = resp.json()
            text = data.get("content", [{}])[0].get("text", "")
            return JSONResponse({"ok": True, "text": text, "words": len(text.split()), "filename": file.filename})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OCR Tool</title>
<style>
:root { --bg:#0a0a0f; --surface:#12121a; --elevated:#1a1a28; --border:#252538; --text:#e8e8f0; --text2:#8888a0; --accent:#6366f1; --green:#22c55e; --radius:10px; }
* { margin:0; padding:0; box-sizing:border-box; }
body { background:var(--bg); color:var(--text); font-family:-apple-system,system-ui,sans-serif; min-height:100vh; display:flex; }

/* Sidebar */
.sidebar { width:260px; background:var(--surface); border-right:1px solid var(--border); padding:24px 16px; display:flex; flex-direction:column; gap:16px; }
.sidebar h1 { font-size:18px; font-weight:700; }
.sidebar .btn-primary { width:100%; padding:12px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius); font-size:14px; font-weight:600; cursor:pointer; }
.sidebar .btn-primary:hover { background:#818cf8; }
.stat-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.stat { background:var(--elevated); border-radius:8px; padding:12px; text-align:center; }
.stat-value { font-size:24px; font-weight:700; color:var(--accent); }
.stat-label { font-size:11px; color:var(--text2); margin-top:2px; }
.quick-list { display:flex; flex-direction:column; gap:4px; }
.quick-item { padding:10px 12px; border-radius:8px; cursor:pointer; font-size:13px; color:var(--text2); transition:all .15s; display:flex; align-items:center; gap:8px; }
.quick-item:hover { background:var(--elevated); color:var(--text); }
.section-title { font-size:11px; text-transform:uppercase; letter-spacing:1px; color:var(--text2); margin:8px 0 4px; }

/* Main — split view */
.main { flex:1; display:flex; gap:0; height:100vh; overflow:hidden; }
.panel-left { flex:1; padding:24px; overflow-y:auto; border-right:1px solid var(--border); }
.panel-right { flex:1; padding:24px; display:flex; flex-direction:column; }
.panel-left h2 { font-size:20px; margin-bottom:4px; }
.panel-left .subtitle { color:var(--text2); font-size:13px; margin-bottom:20px; }

/* Upload */
.upload-zone { border:2px dashed var(--border); border-radius:var(--radius); padding:40px 24px; text-align:center; cursor:pointer; transition:all .2s; margin-bottom:16px; }
.upload-zone:hover, .upload-zone.dragover { border-color:var(--accent); background:rgba(99,102,241,.1); }
.upload-zone.dragover { border-style:solid; transform:scale(1.01); }
.upload-zone .icon { font-size:40px; opacity:.3; margin-bottom:8px; }
.upload-zone p { color:var(--text2); font-size:13px; }
.upload-zone .filename { color:var(--green); font-size:12px; margin-top:6px; }

/* URL input */
.url-row { display:flex; gap:8px; margin-bottom:16px; }
.url-row input { flex:1; padding:10px 14px; background:var(--elevated); border:1px solid var(--border); border-radius:8px; color:var(--text); font-size:13px; outline:none; }
.url-row input:focus { border-color:var(--accent); }
.url-row button { padding:10px 18px; background:var(--accent); color:#fff; border:none; border-radius:8px; font-weight:600; cursor:pointer; white-space:nowrap; font-size:13px; }

/* Options */
.options { display:flex; gap:8px; margin-bottom:16px; }
.options select { padding:7px 10px; background:var(--elevated); border:1px solid var(--border); border-radius:8px; color:var(--text); font-size:12px; }

/* Preview */
.preview-img { max-width:100%; max-height:200px; border-radius:8px; margin-bottom:12px; object-fit:contain; }

/* Result — right panel */
.result-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }
.result-header h3 { font-size:15px; }
.result-header .badge { background:rgba(34,197,94,.15); color:var(--green); padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.result-textarea { flex:1; width:100%; background:var(--elevated); border:1px solid var(--border); border-radius:8px; padding:16px; font-size:14px; line-height:1.7; color:var(--text); font-family:inherit; resize:none; outline:none; }
.result-textarea:focus { border-color:var(--accent); }
.result-textarea::placeholder { color:var(--text2); }
.result-actions { display:flex; gap:8px; margin-top:10px; flex-shrink:0; }
.result-actions button { padding:8px 16px; border-radius:8px; font-size:13px; font-weight:500; cursor:pointer; border:1px solid var(--border); background:none; color:var(--text); }
.result-actions button:hover { border-color:var(--accent); }
.result-actions button.primary { background:var(--accent); color:#fff; border-color:var(--accent); }
.empty-result { flex:1; display:flex; align-items:center; justify-content:center; color:var(--text2); font-size:14px; text-align:center; }

/* Loading */
.loading { display:none; flex:1; align-items:center; justify-content:center; flex-direction:column; }
.spinner { width:32px; height:32px; border:3px solid var(--border); border-top-color:var(--accent); border-radius:50%; animation:spin .6s linear infinite; margin-bottom:12px; }
@keyframes spin { to{transform:rotate(360deg)} }
</style>
</head>
<body>
<div class="sidebar">
    <h1>OCR Tool</h1>
    <button class="btn-primary" onclick="document.getElementById('url-input').focus()">New Extraction</button>
    <div class="stat-grid">
        <div class="stat"><div class="stat-value" id="stat-count">0</div><div class="stat-label">Extractions</div></div>
        <div class="stat"><div class="stat-value" id="stat-words">0</div><div class="stat-label">Words</div></div>
    </div>
    <div class="section-title">Quick Tools</div>
    <div class="quick-list">
        <div class="quick-item" onclick="document.getElementById('url-input').focus()">📷 Screenshot OCR</div>
        <div class="quick-item" onclick="document.getElementById('url-input').focus()">🧾 Receipt Scanner</div>
        <div class="quick-item" onclick="document.getElementById('url-input').focus()">📄 Document OCR</div>
        <div class="quick-item" onclick="setFormat('markdown')">📝 Extract as Markdown</div>
    </div>
</div>
<div class="main">
    <!-- LEFT: Upload -->
    <div class="panel-left">
        <h2>Extract Text</h2>
        <p class="subtitle">Upload image, paste from clipboard, or enter URL</p>

        <div class="upload-zone" id="drop-zone" onclick="document.getElementById('file-input').click()">
            <div class="icon">📸</div>
            <p>Click to choose file, drag & drop, or Ctrl+V</p>
            <div class="filename" id="filename"></div>
            <input type="file" id="file-input" accept="image/*" style="display:none" onchange="uploadFile(this.files[0])" />
        </div>

        <img id="preview-img" class="preview-img" style="display:none" />

        <div class="url-row">
            <input id="url-input" placeholder="Or paste image URL..." />
            <button onclick="extract()">Extract</button>
        </div>

        <div class="options">
            <select id="format-select">
                <option value="plain">Plain Text</option>
                <option value="markdown">Markdown</option>
                <option value="json">JSON</option>
                <option value="structured">Document</option>
            </select>
            <select id="lang-select">
                <option value="auto">Auto</option>
                <option value="en">EN</option>
                <option value="ru">RU</option>
                <option value="es">ES</option>
                <option value="de">DE</option>
            </select>
        </div>
    </div>

    <!-- RIGHT: Result -->
    <div class="panel-right">
        <div class="result-header">
            <h3>Extracted Text</h3>
            <span class="badge" id="word-badge"></span>
        </div>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="color:var(--text2)">Extracting text...</p>
        </div>

        <div class="empty-result" id="empty-result">
            Upload an image to see extracted text here
        </div>

        <textarea class="result-textarea" id="result-text" style="display:none" placeholder="Extracted text will appear here..." readonly></textarea>

        <div class="result-actions" id="result-actions" style="display:none">
            <button class="primary" onclick="copyText()">Copy All</button>
            <button onclick="copySelected()">Copy Selected</button>
            <button onclick="enableEdit()">Edit</button>
            <button onclick="extract()">Re-extract</button>
        </div>
    </div>
</div>
<script>
let totalCount = 0, totalWords = 0;
function setFormat(f) { document.getElementById('format-select').value = f; }

function showResult(text, words) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('empty-result').style.display = 'none';
    document.getElementById('result-text').style.display = '';
    document.getElementById('result-actions').style.display = '';
    document.getElementById('result-text').value = text;
    document.getElementById('result-text').readOnly = true;
    document.getElementById('word-badge').textContent = words + ' words';
    totalCount++; totalWords += words;
    document.getElementById('stat-count').textContent = totalCount;
    document.getElementById('stat-words').textContent = totalWords;
}

function showLoading() {
    document.getElementById('loading').style.display = 'flex';
    document.getElementById('empty-result').style.display = 'none';
    document.getElementById('result-text').style.display = 'none';
    document.getElementById('result-actions').style.display = 'none';
}

function showPreview(src) {
    var img = document.getElementById('preview-img');
    img.src = src;
    img.style.display = '';
}

async function extract() {
    var url = document.getElementById('url-input').value.trim();
    if (!url) return alert('Paste an image URL');
    showLoading();
    showPreview(url);
    try {
        var r = await fetch('/api/extract', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({image_url: url, format: document.getElementById('format-select').value, language: document.getElementById('lang-select').value})
        });
        var d = await r.json();
        if (d.ok) { showResult(d.text, d.words); }
        else { document.getElementById('loading').style.display = 'none'; alert('Error: ' + d.error); }
    } catch(e) { document.getElementById('loading').style.display = 'none'; alert(e); }
}

function copyText() {
    var ta = document.getElementById('result-text');
    navigator.clipboard.writeText(ta.value);
    document.querySelector('.result-actions .primary').textContent = 'Copied!';
    setTimeout(function() { document.querySelector('.result-actions .primary').textContent = 'Copy All'; }, 2000);
}

function copySelected() {
    var ta = document.getElementById('result-text');
    var selected = ta.value.substring(ta.selectionStart, ta.selectionEnd);
    if (selected) {
        navigator.clipboard.writeText(selected);
        alert('Copied selected text (' + selected.split(' ').length + ' words)');
    } else {
        alert('Select some text first');
    }
}

function enableEdit() {
    var ta = document.getElementById('result-text');
    ta.readOnly = !ta.readOnly;
    ta.style.borderColor = ta.readOnly ? '' : 'var(--accent)';
}
document.getElementById('url-input').addEventListener('keydown', e => { if (e.key === 'Enter') extract(); });

// File upload
async function uploadFile(file) {
    if (!file) return;
    document.getElementById('filename').textContent = file.name;
    // Preview
    var reader = new FileReader();
    reader.onload = function(e) { showPreview(e.target.result); };
    reader.readAsDataURL(file);

    showLoading();
    var formData = new FormData();
    formData.append('file', file);
    try {
        var r = await fetch('/api/upload', { method: 'POST', body: formData });
        var d = await r.json();
        if (d.ok) { showResult(d.text, d.words); }
        else { document.getElementById('loading').style.display = 'none'; alert('Error: ' + d.error); }
    } catch(e) { document.getElementById('loading').style.display = 'none'; alert(e); }
}

// Drag & drop
const dropZone = document.getElementById('drop-zone');
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) uploadFile(file);
    else alert('Please drop an image file');
});

// Paste from clipboard
document.addEventListener('paste', e => {
    const items = e.clipboardData.items;
    for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
            const file = items[i].getAsFile();
            uploadFile(file);
            break;
        }
    }
});
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML

if __name__ == "__main__":
    print("\n  OCR Tool → http://localhost:8911\n")
    uvicorn.run(app, host="127.0.0.1", port=8911, log_level="warning")
