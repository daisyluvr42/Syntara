"""Corpus (user custom knowledge base) models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CorpusFileType(str, Enum):
    md = "md"
    txt = "txt"
    pdf = "pdf"


class Corpus(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str | None = None
    file_path: str
    file_type: CorpusFileType = CorpusFileType.md
    file_hash: str = ""
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CorpusCreate(BaseModel):
    title: str = ""
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
