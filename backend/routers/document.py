"""Document CRUD API router."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db.sqlite import get_connection
from backend.models.document import DocumentCreate, DocumentUpdate

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
async def list_documents(skip: int = 0, limit: int = 50):
    """List all writing documents."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, csl_style, created_at, updated_at FROM document ORDER BY updated_at DESC LIMIT ? OFFSET ?",
        (limit, skip),
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) as c FROM document").fetchone()["c"]
    return {"items": [dict(r) for r in rows], "total": total}


@router.get("/{doc_id}")
async def get_document(doc_id: str):
    """Get a single document with full content."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM document WHERE id = ?", (doc_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Document not found")
    return dict(row)


@router.post("")
async def create_document(data: DocumentCreate):
    """Create a new writing document."""
    conn = get_connection()
    doc_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    conn.execute(
        "INSERT INTO document (id, title, content, csl_style, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        (doc_id, data.title, data.content, data.csl_style, now, now),
    )
    conn.commit()
    return {"id": doc_id, "title": data.title}


@router.put("/{doc_id}")
async def update_document(doc_id: str, data: DocumentUpdate):
    """Update a document."""
    conn = get_connection()
    row = conn.execute("SELECT id FROM document WHERE id = ?", (doc_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Document not found")

    updates = {
        field: ("" if value is None else value)
        for field, value in data.model_dump(exclude_unset=True).items()
    }
    updates["updated_at"] = datetime.now().isoformat()

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [doc_id]
    conn.execute(f"UPDATE document SET {set_clause} WHERE id = ?", values)
    conn.commit()
    return {"ok": True}


@router.post("/{doc_id}/beacon-save")
async def beacon_save_document(doc_id: str, data: DocumentUpdate):
    """Emergency save via navigator.sendBeacon (POST-only, for page unload)."""
    conn = get_connection()
    row = conn.execute("SELECT id FROM document WHERE id = ?", (doc_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Document not found")

    updates = {
        field: ("" if value is None else value)
        for field, value in data.model_dump(exclude_unset=True).items()
    }
    updates["updated_at"] = datetime.now().isoformat()

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [doc_id]
    conn.execute(f"UPDATE document SET {set_clause} WHERE id = ?", values)
    conn.commit()
    return {"ok": True}


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and its citations."""
    conn = get_connection()
    row = conn.execute("SELECT id FROM document WHERE id = ?", (doc_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Document not found")
    conn.execute("DELETE FROM citation WHERE document_id = ?", (doc_id,))
    conn.execute("DELETE FROM document WHERE id = ?", (doc_id,))
    conn.commit()
    return {"ok": True}


@router.get("/{doc_id}/citations")
async def get_document_citations(doc_id: str):
    """Get all citations in a document."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT c.*, l.title as lit_title, l.authors, l.year, l.journal
           FROM citation c
           JOIN literature l ON c.literature_id = l.id
           WHERE c.document_id = ?
           ORDER BY c."order" """,
        (doc_id,),
    ).fetchall()

    items = []
    for r in rows:
        item = dict(r)
        item["authors"] = json.loads(item["authors"]) if item["authors"] else []
        items.append(item)
    return items


@router.post("/{doc_id}/citations")
async def add_citation(doc_id: str, literature_id: str, cite_key: str, position: int = 0, context: str = ""):
    """Add a citation to a document."""
    conn = get_connection()

    # Get next order number
    max_order = conn.execute(
        "SELECT MAX(\"order\") as m FROM citation WHERE document_id = ?", (doc_id,)
    ).fetchone()["m"]
    next_order = (max_order or 0) + 1

    cit_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO citation (id, document_id, literature_id, cite_key, position, context, "order")
           VALUES (?,?,?,?,?,?,?)""",
        (cit_id, doc_id, literature_id, cite_key, position, context, next_order),
    )
    conn.commit()
    return {"id": cit_id, "order": next_order}


@router.delete("/{doc_id}/citations/{cit_id}")
async def remove_citation(doc_id: str, cit_id: str):
    """Remove a citation from a document."""
    conn = get_connection()
    conn.execute("DELETE FROM citation WHERE id = ? AND document_id = ?", (cit_id, doc_id))
    conn.commit()
    return {"ok": True}


class FormatCitationsRequest(BaseModel):
    content: str
    style: str = "vancouver"  # vancouver, apa, gb-t-7714


@router.post("/format-citations")
async def format_citations_endpoint(req: FormatCitationsRequest):
    """Format all citations in the content according to the selected style.

    Idempotent: re-formats previously formatted content by reverting first.
    Supported styles: vancouver, apa, gb-t-7714.
    """
    from backend.services.exporter import format_citations

    formatted = format_citations(req.content, style=req.style)
    return {"content": formatted}


@router.post("/unformat-citations")
async def unformat_citations_endpoint(req: FormatCitationsRequest):
    """Revert formatted citations back to [@citekey] markers."""
    from backend.services.exporter import revert_formatted_citations

    raw = revert_formatted_citations(req.content)
    return {"content": raw}
