"""Writing document models."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "Untitled"
    content: str = ""
    csl_style: str = "vancouver"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class DocumentCreate(BaseModel):
    title: str = "Untitled"
    content: str = ""
    csl_style: str = "vancouver"


class DocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    csl_style: str | None = None
