"""Citation record models."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class Citation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    literature_id: str
    cite_key: str
    position: int = 0
    context: str = ""
    order: int = 0


class CitationCreate(BaseModel):
    document_id: str
    literature_id: str
    cite_key: str
    position: int = 0
    context: str = ""
    order: int = 0
