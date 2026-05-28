"""Corpus management API router."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.config import CORPUS_DIR
from backend.db.sqlite import get_connection
from backend.models.corpus import CorpusCreate
from backend.services.corpus import import_corpus_file
from backend.services.indexer import remove_index

router = APIRouter(prefix="/api/corpus", tags=["corpus"])


@router.get("")
async def list_corpus(skip: int = 0, limit: int = 50, tag: str | None = None):
    """List all corpus entries."""
    conn = get_connection()
    query = "SELECT * FROM corpus"
    params: list = []

    if tag:
        query += " WHERE tags LIKE ?"
        params.append(f"%{tag}%")

    query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, skip])

    rows = conn.execute(query, params).fetchall()
    total = conn.execute("SELECT COUNT(*) as c FROM corpus").fetchone()["c"]

    items = []
    for r in rows:
        item = dict(r)
        item["tags"] = json.loads(item["tags"]) if item["tags"] else []
        items.append(item)

    return {"items": items, "total": total}


@router.get("/{corpus_id}")
async def get_corpus(corpus_id: str):
    """Get a single corpus entry."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM corpus WHERE id = ?", (corpus_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Corpus entry not found")
    item = dict(row)
    item["tags"] = json.loads(item["tags"]) if item["tags"] else []
    return item


@router.post("/upload")
async def upload_corpus(
    file: UploadFile = File(...),
    title: str = "",
    description: str = "",
    tags: str = "",
):
    """Upload a file to the corpus."""
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    allowed_ext = {".md", ".txt", ".pdf", ".markdown", ".text"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_ext:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    # Save file
    dest = CORPUS_DIR / file.filename
    counter = 1
    while dest.exists():
        stem = Path(file.filename).stem
        dest = CORPUS_DIR / f"{stem}_{counter}{ext}"
        counter += 1

    with open(dest, "wb") as f:
        content = await file.read()
        f.write(content)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    corpus = await import_corpus_file(dest, title=title, description=description, tags=tag_list)
    if not corpus:
        dest.unlink(missing_ok=True)
        raise HTTPException(409, "Duplicate file or import failed")

    return {"id": corpus.id, "title": corpus.title}


@router.delete("/{corpus_id}")
async def delete_corpus(corpus_id: str):
    """Delete a corpus entry and its indexes."""
    conn = get_connection()
    row = conn.execute("SELECT id FROM corpus WHERE id = ?", (corpus_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Corpus entry not found")

    conn.execute("DELETE FROM corpus WHERE id = ?", (corpus_id,))
    conn.execute("DELETE FROM corpus_fts WHERE corpus_id = ?", (corpus_id,))
    conn.commit()

    await remove_index(corpus_id)
    return {"ok": True}


@router.put("/{corpus_id}/tags")
async def update_corpus_tags(corpus_id: str, tags: list[str]):
    """Update tags for a corpus entry."""
    conn = get_connection()
    conn.execute(
        "UPDATE corpus SET tags = ?, updated_at = ? WHERE id = ?",
        (json.dumps(tags), datetime.now().isoformat(), corpus_id),
    )
    conn.commit()
    return {"ok": True}
