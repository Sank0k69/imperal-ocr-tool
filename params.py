"""Pydantic models for chat-function parameters."""
from pydantic import BaseModel


class ExtractParams(BaseModel):
    """Extract text from a single image supplied as base64."""
    image_b64: str = ""       # raw base64, no data: prefix
    language: str = "auto"    # eng | rus | spa | deu | fra | auto (eng+rus)
    preserve_layout: bool = False


class HistoryQueryParams(BaseModel):
    """Read the user's past extractions."""
    limit: int = 20


class SaveSettingsParams(BaseModel):
    """Form payload for OCR Tool settings."""
    server_url: str = ""
    server_api_key: str = ""
    default_language: str = ""
    preserve_layout: bool = False
    save_history: bool = True
