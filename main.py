"""
OCR Tool — Extract text from images.
Enterprise-grade image-to-text extraction for Imperal Cloud.

Features:
- Upload image → AI extracts text → copy/edit/export
- Batch processing (multiple images)
- History of extractions
- Format options: plain text, markdown, JSON
- Language detection
- Translate extracted text
- Summarize long documents
"""
from __future__ import annotations
import time
from pydantic import BaseModel, Field
from imperal_sdk import Extension, ChatExtension, ActionResult
from imperal_sdk.ui import (
    Page, Section, Stack, Grid, Tabs,
    Header, Text, Stat, Stats, Badge, Divider,
    Card, Button, Image,
    FileUpload, TextArea, Input, Select,
    List, ListItem, Empty, Alert, Markdown,
    KeyValue,
    Call, Send,
)

ext = Extension("ocr-tool", version="1.0.0", config_defaults={
    "default_format": "plain",
    "default_language": "auto",
    "save_history": True,
})

chat = ChatExtension(
    ext,
    tool_name="ocr",
    description="Extract text from images. Upload screenshots, photos, documents, receipts, "
                "handwritten notes — get accurate, copyable text back.",
    system_prompt="You are an OCR specialist. When given an image, extract ALL visible text accurately. "
                  "Preserve formatting, tables, and structure. Support multiple languages.",
    max_rounds=8,
)


# ======================================================================
# Chat Functions
# ======================================================================

class ExtractParams(BaseModel):
    image_url: str = Field(default="", description="URL of image to process")
    format: str = Field(default="plain", description="Output: plain, markdown, json, structured")
    language: str = Field(default="auto", description="Language: auto, en, ru, es, de, fr, zh, ja")
    instructions: str = Field(default="", description="Special instructions")

@chat.function("extract", description="Extract text from an uploaded image", action_type="read")
async def extract_text(ctx, params: ExtractParams) -> ActionResult:
    """Extract text from an image using AI vision."""
    if not params.image_url:
        return ActionResult.error("Upload an image first, or paste an image URL.")

    format_map = {
        "plain": "Return extracted text as plain text. Preserve line breaks.",
        "markdown": "Return as Markdown with headers, lists, tables where appropriate.",
        "json": 'Return as JSON: {"blocks": [{"type": "heading|paragraph|table", "text": "..."}]}',
        "structured": "Identify document structure: title, sections, key-value pairs. Organize clearly.",
    }
    fmt = format_map.get(params.format, format_map["plain"])
    lang = f" Text is likely in {params.language}." if params.language != "auto" else ""
    extra = f" {params.instructions}" if params.instructions else ""

    result = await ctx.ai.complete(
        f"Extract ALL text from this image accurately.{lang} {fmt}{extra}",
        system="Precise OCR tool. Extract text with high accuracy. Preserve structure.",
    )

    word_count = len(result.text.split())
    if ctx.config.get("save_history", True):
        await ctx.store.create("ocr_history", {
            "text": result.text[:500],
            "word_count": word_count,
            "format": params.format,
            "timestamp": time.time(),
        })

    return ActionResult.success(
        data={"text": result.text, "word_count": word_count, "format": params.format},
        summary=f"Extracted {word_count} words ({params.format})",
    )


class TranslateParams(BaseModel):
    text: str = Field(description="Text to translate")
    target_language: str = Field(default="en", description="Target: en, ru, es, de, fr")

@chat.function("translate", description="Translate extracted text", action_type="read")
async def translate_text(ctx, params: TranslateParams) -> ActionResult:
    """Translate text to another language."""
    result = await ctx.ai.complete(
        f"Translate to {params.target_language}. Only the translation:\n\n{params.text}",
        system="Translate accurately, preserving meaning.",
    )
    return ActionResult.success(
        data={"translated": result.text, "language": params.target_language},
        summary=f"Translated to {params.target_language}",
    )


class SummarizeParams(BaseModel):
    text: str = Field(description="Text to summarize")

@chat.function("summarize", description="Summarize extracted text", action_type="read")
async def summarize_text(ctx, params: SummarizeParams) -> ActionResult:
    """Summarize long text into key points."""
    result = await ctx.ai.complete(
        f"Summarize in 3 sentences:\n\n{params.text}",
        system="Concise summaries. Keep key information.",
    )
    return ActionResult.success(
        data={"summary": result.text},
        summary=f"Summarized {len(params.text.split())} words",
    )


# ======================================================================
# DUI Panels
# ======================================================================

@ext.panel("workspace", slot="main", title="OCR Tool", icon="scan")
async def workspace_panel(ctx):
    """Main workspace — extract tab + history tab."""
    history = await ctx.store.query("ocr_history", {})
    items = history if isinstance(history, list) else []

    return Page(
        title="OCR Tool",
        subtitle="Extract text from any image",
        children=[
            Tabs(tabs=[
                {"id": "extract", "label": "Extract", "content": _extract_tab()},
                {"id": "history", "label": "History", "content": _history_tab(items)},
            ]),
        ],
    )


def _extract_tab():
    return Stack(children=[
        Section(
            title="Upload Image",
            children=[
                FileUpload(
                    accept="image/*",
                    max_size_mb=10,
                    on_upload=Call(function="extract"),
                    param_name="image_url",
                ),
            ],
        ),
        Divider(),
        Section(
            title="Options",
            collapsible=True,
            children=[
                Stack(direction="h", children=[
                    Select(
                        options=[
                            {"value": "plain", "label": "Plain Text"},
                            {"value": "markdown", "label": "Markdown"},
                            {"value": "json", "label": "JSON"},
                            {"value": "structured", "label": "Document"},
                        ],
                        value="plain",
                        param_name="format",
                        placeholder="Format",
                    ),
                    Select(
                        options=[
                            {"value": "auto", "label": "Auto-detect"},
                            {"value": "en", "label": "English"},
                            {"value": "ru", "label": "Russian"},
                            {"value": "es", "label": "Spanish"},
                            {"value": "de", "label": "German"},
                        ],
                        value="auto",
                        param_name="language",
                        placeholder="Language",
                    ),
                ]),
                Input(
                    placeholder="Special instructions: 'only prices', 'ignore watermarks'...",
                    param_name="instructions",
                ),
            ],
        ),
        Divider(),
        Stack(direction="h", children=[
            Button(
                label="Screenshot OCR",
                variant="secondary",
                icon="monitor",
                on_click=Send(message="Extract text from my screenshot"),
            ),
            Button(
                label="Receipt Scanner",
                variant="secondary",
                icon="receipt",
                on_click=Send(message="Extract data from a receipt"),
            ),
            Button(
                label="Batch (multi)",
                variant="secondary",
                icon="layers",
                on_click=Send(message="I want to extract text from multiple images"),
            ),
        ]),
    ])


def _history_tab(items):
    if not items:
        return Empty(message="No extractions yet", icon="scan")

    list_items = []
    for h in sorted(items, key=lambda x: x.get("timestamp", 0), reverse=True)[:20]:
        list_items.append(ListItem(
            id=str(h.get("timestamp", 0)),
            title=f"{h.get('word_count', 0)} words",
            subtitle=h.get("text", "")[:60],
            meta=h.get("format", "plain"),
            icon="file-text",
            badge=Badge(label=h.get("format", ""), color="blue"),
        ))

    return Stack(children=[
        Stats(children=[
            Stat(label="Total", value=str(len(items)), icon="scan"),
            Stat(label="Words", value=str(sum(h.get("word_count", 0) for h in items)), icon="type"),
        ]),
        Divider(),
        List(items=list_items),
    ])


@ext.panel("sidebar", slot="left", title="OCR Tool", icon="scan")
async def sidebar_panel(ctx):
    """Left sidebar — stats + quick tools."""
    history = await ctx.store.query("ocr_history", {})
    count = len(history) if isinstance(history, list) else 0

    return Page(
        title="OCR Tool",
        children=[
            Button(
                label="New Extraction",
                variant="primary",
                icon="plus",
                full_width=True,
                on_click=Send(message="I want to extract text from an image"),
            ),
            Divider(),
            Stats(children=[
                Stat(label="Extractions", value=str(count), icon="scan"),
            ]),
            Divider(),
            Section(
                title="Quick Tools",
                collapsible=True,
                children=[
                    List(items=[
                        ListItem(id="screenshot", title="Screenshot OCR", icon="monitor",
                                 on_click=Send(message="Extract text from my screenshot")),
                        ListItem(id="receipt", title="Receipt Scanner", icon="file-text",
                                 on_click=Send(message="Scan a receipt image")),
                        ListItem(id="translate", title="Extract & Translate", icon="languages",
                                 on_click=Send(message="Extract and translate to English")),
                        ListItem(id="summarize", title="Extract & Summarize", icon="align-left",
                                 on_click=Send(message="Extract text and summarize it")),
                    ]),
                ],
            ),
        ],
    )


# ======================================================================
# Lifecycle
# ======================================================================

@ext.on_install
async def on_install(ctx):
    return ActionResult.success(summary="OCR Tool installed! Upload any image to extract text.")

@ext.health_check
async def health(ctx):
    return ActionResult.success(data={"status": "healthy", "version": "1.0.0"})
