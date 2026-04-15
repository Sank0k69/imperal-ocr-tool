"""
OCR Tool — Extract text from images.
Upload an image, get text back. Simple and useful.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from imperal_sdk import Extension, ChatExtension, ActionResult
from imperal_sdk.ui import (
    Page, Section, Stack, Header, Text, Button, Card,
    FileUpload, TextArea, Badge, Stat, Stats, Divider,
    Call,
)

ext = Extension("ocr-tool", version="1.0.0", config_defaults={})

chat = ChatExtension(
    ext,
    tool_name="ocr",
    description="Extract text from images. Upload a photo, screenshot, or document image — get copyable text back.",
    system_prompt="You are an OCR assistant. When given an image, extract ALL visible text from it accurately. "
                  "Preserve formatting where possible. Return the extracted text clearly.",
    max_rounds=5,
)


# ── Chat Functions ──

class ExtractParams(BaseModel):
    image_url: str = Field(default="", description="URL of image to extract text from")
    instructions: str = Field(default="", description="Additional instructions (e.g. 'only extract the title')")

@chat.function("extract_text", description="Extract text from an uploaded image", action_type="read")
async def extract_text(ctx, params: ExtractParams) -> ActionResult:
    """Extract text from an image using AI vision."""
    if not params.image_url:
        return ActionResult.error("Please upload an image first")
    
    prompt = f"Extract ALL text from this image. Return only the extracted text, nothing else."
    if params.instructions:
        prompt += f" Additional instruction: {params.instructions}"
    
    result = await ctx.ai.complete(prompt, system="You are an OCR tool. Extract text from images accurately.")
    return ActionResult.success(
        data={"text": result.text, "source": params.image_url},
        summary=f"Extracted {len(result.text.split())} words",
    )


# ── DUI Panels ──

@ext.panel("main", slot="main", title="OCR Tool", icon="scan")
async def main_panel(ctx):
    history = await ctx.store.query("ocr_history", {})
    count = len(history) if isinstance(history, list) else 0
    
    return Page(
        title="OCR Tool",
        subtitle="Extract text from any image",
        children=[
            Section(
                title="Upload Image",
                children=[
                    FileUpload(
                        accept="image/*",
                        max_size_mb=10,
                        on_upload=Call(function="extract_text"),
                        param_name="image_url",
                    ),
                    Text(content="Upload a screenshot, photo, or document image to extract text.", variant="caption"),
                ],
            ),
            Divider(),
            Section(
                title="How to use",
                children=[
                    Text(content="1. Upload an image or send it in chat", variant="body"),
                    Text(content="2. AI extracts all visible text", variant="body"),
                    Text(content="3. Copy the result", variant="body"),
                ],
            ),
        ],
    )


@ext.panel("sidebar", slot="left", title="History", icon="history")
async def sidebar_panel(ctx):
    return Page(
        title="OCR Tool",
        children=[
            Stats(children=[
                Stat(label="Extractions", value="0", icon="scan"),
            ]),
            Divider(),
            Text(content="Upload an image to get started.", variant="caption"),
        ],
    )


# ── Lifecycle ──

@ext.on_install
async def on_install(ctx):
    return ActionResult.success(summary="OCR Tool installed! Upload any image to extract text.")

@ext.health_check
async def health(ctx):
    return ActionResult.success(data={"status": "healthy"})
