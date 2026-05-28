"""Literature data models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LiteratureType(str, Enum):
    journal_article = "journal_article"
    book_chapter = "book_chapter"
    conference = "conference"
    thesis = "thesis"
    report = "report"
    other = "other"


class Author(BaseModel):
    family: str
    given: str = ""
    affiliation: Optional[str] = None


class Literature(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cite_key: str = ""

    # Core metadata
    title: str = ""
    authors: list[Author] = Field(default_factory=list)
    abstract: Optional[str] = None

    # Publication info
    journal: Optional[str] = None
    publisher: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    year: Optional[int] = None
    date: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    issn: Optional[str] = None
    isbn: Optional[str] = None

    # Classification
    type: LiteratureType = LiteratureType.journal_article
    keywords: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    language: str = "en"

    # File & index
    file_path: Optional[str] = None
    file_hash: Optional[str] = None
    file_size: Optional[int] = None
    full_text: Optional[str] = None
    processing_status: str = "ready"
    processing_error: Optional[str] = None
    search_ready_fts: bool = False
    search_ready_vector: bool = False

    # Metadata quality
    metadata_sources: dict[str, str] = Field(default_factory=dict)
    metadata_confidence: float = 0.0
    manually_verified: bool = False

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    imported_at: datetime = Field(default_factory=datetime.now)


class LiteratureCreate(BaseModel):
    title: str = ""
    authors: list[Author] = Field(default_factory=list)
    abstract: Optional[str] = None
    journal: Optional[str] = None
    publisher: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    year: Optional[int] = None
    date: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    issn: Optional[str] = None
    isbn: Optional[str] = None
    type: LiteratureType = LiteratureType.journal_article
    keywords: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    language: str = "en"


class LiteratureUpdate(BaseModel):
    title: Optional[str] = None
    authors: Optional[list[Author]] = None
    abstract: Optional[str] = None
    journal: Optional[str] = None
    publisher: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    year: Optional[int] = None
    date: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    issn: Optional[str] = None
    isbn: Optional[str] = None
    type: Optional[LiteratureType] = None
    keywords: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    language: Optional[str] = None
    manually_verified: Optional[bool] = None
