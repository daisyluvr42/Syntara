"""Text chunk models for vector search."""

from __future__ import annotations

import uuid
from enum import Enum

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    literature = "literature"
    corpus = "corpus"


class ElementType(str, Enum):
    paragraph = "paragraph"
    heading = "heading"
    caption = "caption"
    table = "table"
    text_block = "text_block"
    list = "list"


class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    source_type: SourceType = SourceType.literature
    content: str
    chunk_index: int = 0
    token_count: int = 0

    # Structured metadata from opendataloader-pdf
    element_type: ElementType = ElementType.paragraph
    heading: str = ""          # Nearest preceding heading text
    page_number: int = 0
    bbox: list[float] | None = None  # [x0, y0, x1, y1]
