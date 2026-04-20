"""Pydantic models for chat-function parameters.

The FileUpload component ships payloads as ``list[dict]`` (each dict
has ``data_base64``, ``name``, ``size``, ``content_type``). We accept
both that shape and a raw string so IPC callers and automations can
still pass a bare base64 blob.
"""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


Language = Literal["auto", "eng", "rus", "spa", "deu", "fra"]


class ExtractParams(BaseModel):
    """Drop an image, get the text. Accepts FileUpload payload or raw b64."""
    # FileUpload sends list[dict]; IPC can still pass a bare base64 string.
    model_config = ConfigDict(arbitrary_types_allowed=True)
    image_b64: Any = Field(default=None,
                           description="FileUpload payload (list[dict]) or raw base64 string")
    language: Language = Field(default="auto",
                               description="OCR language code")
    preserve_layout: bool = Field(default=False,
                                  description="Keep columns/tables — --psm 4")


class HistoryQueryParams(BaseModel):
    """Read the user's past extractions."""
    limit: int = Field(default=20, ge=1, le=100)


class SaveSettingsParams(BaseModel):
    """User preferences. Server URL / API key are not here — they're baked
    into the extension and shared by every install."""
    default_language: Language = "auto"
    preserve_layout: bool = False
    save_history: bool = True
