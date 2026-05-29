"""Reusable writing style profile models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class StyleProfileBuildRequest(BaseModel):
    name: str
    project: str = "default"
    style_type: str | None = None
    corpus_ids: list[str] = Field(default_factory=list)
    tag: str | None = None
    content: str | None = None
    source_title: str | None = None
    provider_id: str | None = None
    set_default: bool = True


class StyleProfileSaveRequest(BaseModel):
    name: str
    project: str = "default"
    style_type: str | None = None
    profile_json: dict = Field(default_factory=dict)
    profile_markdown: str
    source_corpus_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    set_default: bool = True


class StyleProfileRevisionRequest(BaseModel):
    original_text: str
    revised_text: str
    base_profile_id: str | None = None
    name: str | None = None
    project: str = "default"
    style_type: str | None = None
    source_title: str | None = None
    provider_id: str | None = None
    set_default: bool = True


class StyleProfileSummary(BaseModel):
    id: str
    name: str
    project: str
    style_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_default: bool = False
    created_at: datetime
    updated_at: datetime


class StyleProfile(BaseModel):
    id: str
    name: str
    project: str
    style_type: str | None = None
    profile_json: dict
    profile_markdown: str
    source_corpus_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    is_default: bool = False
    created_at: datetime
    updated_at: datetime
