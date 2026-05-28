"""Search API router."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.db.sqlite import get_connection
from backend.services.extract_cache import load_cached
from backend.services.odl_extractor import build_structured_chunks
from backend.services.searcher import grouped_literature_search, hybrid_search

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    scope: str = "all"  # all, literature, corpus
    top_k: int = 20
    project: str | None = None


class GroupedLiteratureSearchRequest(BaseModel):
    zh_query: str = ""
    en_query: str = ""
    provider_id: str | None = None
    top_k: int = 20
    project: str | None = None


@router.post("")
async def search(req: SearchRequest):
    """Perform hybrid search (FTS5 + vector) across literature and/or corpus."""
    results = await hybrid_search(req.query, scope=req.scope, top_k=req.top_k, project=req.project)
    return {"results": results, "total": len(results)}


@router.post("/literature-grouped")
async def search_literature_grouped(req: GroupedLiteratureSearchRequest):
    """Search literature and return grouped document hits with chunk-level evidence."""
    # Save queries to history
    conn = get_connection()
    now = datetime.now().isoformat()
    if req.zh_query.strip():
        conn.execute(
            """INSERT INTO search_history (lang, query, used_at) VALUES ('zh', ?, ?)
               ON CONFLICT(lang, query) DO UPDATE SET used_at = excluded.used_at""",
            (req.zh_query.strip(), now),
        )
    if req.en_query.strip():
        conn.execute(
            """INSERT INTO search_history (lang, query, used_at) VALUES ('en', ?, ?)
               ON CONFLICT(lang, query) DO UPDATE SET used_at = excluded.used_at""",
            (req.en_query.strip(), now),
        )
    conn.commit()

    return await grouped_literature_search(
        zh_query=req.zh_query,
        en_query=req.en_query,
        provider_id=req.provider_id,
        top_k=req.top_k,
        project=req.project,
    )


@router.get("/history")
async def search_history(lang: str = Query(""), prefix: str = Query(""), limit: int = Query(10)):
    """Get search history, optionally filtered by language and prefix."""
    conn = get_connection()
    if prefix.strip():
        rows = conn.execute(
            """SELECT query FROM search_history
               WHERE (lang = ? OR ? = '') AND query LIKE ? || '%'
               ORDER BY used_at DESC LIMIT ?""",
            (lang, lang, prefix.strip(), limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT query FROM search_history
               WHERE lang = ? OR ? = ''
               ORDER BY used_at DESC LIMIT ?""",
            (lang, lang, limit),
        ).fetchall()
    return {"suggestions": [r["query"] for r in rows]}


class ChunkContextRequest(BaseModel):
    lit_id: str
    chunk_index: int


@router.post("/chunk-context")
async def chunk_context(req: ChunkContextRequest):
    """Return the full page text containing the target chunk, with highlight offsets."""
    conn = get_connection()
    row = conn.execute(
        "SELECT file_hash, full_text FROM literature WHERE id = ?",
        (req.lit_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Literature not found")

    file_hash = row["file_hash"]
    chunks: list[dict] = []

    if file_hash:
        elements = load_cached(file_hash)
        if elements:
            chunks = build_structured_chunks(elements)

    if not chunks:
        full_text = (row["full_text"] or "").strip()
        if not full_text:
            raise HTTPException(404, "No content available for this literature")
        paragraphs = [p.strip() for p in full_text.split("\n") if p.strip()]
        buf, idx = "", 0
        for para in paragraphs:
            if len(buf) + len(para) > 500 and buf:
                chunks.append({"content": buf.strip(), "chunk_index": idx,
                               "element_type": "paragraph", "heading": "", "page_number": 0})
                idx += 1
                buf = para
            else:
                buf = (buf + "\n" + para).strip() if buf else para
        if buf.strip():
            chunks.append({"content": buf.strip(), "chunk_index": idx,
                           "element_type": "paragraph", "heading": "", "page_number": 0})

    # Find the target chunk
    target_chunk = None
    for chunk in chunks:
        if chunk["chunk_index"] == req.chunk_index:
            target_chunk = chunk
            break

    if target_chunk is None:
        raise HTTPException(404, "Chunk not found")

    target_page = target_chunk.get("page_number", 0)

    # Collect all chunks on the same page, concatenate into continuous text
    page_chunks = [c for c in chunks if c.get("page_number", 0) == target_page]
    page_chunks.sort(key=lambda c: c["chunk_index"])

    # Build full page text and track target chunk position
    parts: list[str] = []
    highlight_start = -1
    highlight_end = -1
    offset = 0
    for c in page_chunks:
        if parts:
            parts.append("\n\n")
            offset += 2
        if c["chunk_index"] == req.chunk_index:
            highlight_start = offset
        parts.append(c["content"])
        offset += len(c["content"])
        if c["chunk_index"] == req.chunk_index:
            highlight_end = offset

    return {
        "page_number": target_page,
        "page_text": "".join(parts),
        "highlight_start": highlight_start,
        "highlight_end": highlight_end,
    }


# --- Dismissed hits ---

class DismissHitRequest(BaseModel):
    query_key: str
    lit_id: str
    chunk_index: int


@router.post("/dismiss-hit")
async def dismiss_hit(req: DismissHitRequest):
    """Mark a search hit as dismissed for a given query key."""
    conn = get_connection()
    conn.execute(
        """INSERT OR IGNORE INTO dismissed_hits (query_key, lit_id, chunk_index, dismissed_at)
           VALUES (?, ?, ?, ?)""",
        (req.query_key, req.lit_id, req.chunk_index, datetime.now().isoformat()),
    )
    conn.commit()
    return {"ok": True}


@router.post("/restore-hit")
async def restore_hit(req: DismissHitRequest):
    """Restore a previously dismissed hit."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM dismissed_hits WHERE query_key = ? AND lit_id = ? AND chunk_index = ?",
        (req.query_key, req.lit_id, req.chunk_index),
    )
    conn.commit()
    return {"ok": True}


@router.get("/dismissed-hits")
async def get_dismissed_hits(query_key: str = Query(...)):
    """Get all dismissed hit keys for a query key. Returns list of 'lit_id:chunk_index' strings."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT lit_id, chunk_index FROM dismissed_hits WHERE query_key = ?",
        (query_key,),
    ).fetchall()
    return {"dismissed": [f"{r['lit_id']}:{r['chunk_index']}" for r in rows]}
