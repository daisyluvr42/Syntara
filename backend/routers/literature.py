"""Literature CRUD API router."""

from __future__ import annotations

import asyncio
import json
import logging
import multiprocessing
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.config import FILES_DIR
from backend.db import sqlite
from backend.db.sqlite import get_connection, tag_filter_clause
from backend.models.literature import LiteratureCreate, LiteratureUpdate
from backend.services.indexer import index_literature, remove_index
from backend.services.metadata import process_pdf_metadata

logger = logging.getLogger(__name__)


def recover_stuck_processing():
    """Called at startup: mark any 'processing' items as failed (previous crash)."""
    conn = get_connection()
    stuck = conn.execute(
        "SELECT id, title FROM literature WHERE processing_status = 'processing'"
    ).fetchall()
    if not stuck:
        return
    for row in stuck:
        conn.execute(
            """UPDATE literature SET processing_status = 'failed',
               processing_error = 'Server restarted while processing. Click Retry to reprocess.',
               processing_progress = NULL, updated_at = ? WHERE id = ?""",
            (datetime.now().isoformat(), row["id"]),
        )
        logger.warning("Recovered stuck processing item: %s (%s)", row["id"][:12], row["title"][:40])
    conn.commit()
    logger.info("Recovered %d stuck processing items from previous crash", len(stuck))


router = APIRouter(prefix="/api/literature", tags=["literature"])


def _auto_build_doc_tree(lit_id: str, title: str, elements: list[dict]) -> None:
    if not elements:
        return
    from backend.services.doc_tree_builder import build_tree
    from backend.services.doc_tree_cache import save_tree

    tree = build_tree(lit_id, title, elements)
    save_tree(tree)


@router.get("")
async def list_literature(
    skip: int = 0,
    limit: int = 50,
    tag: str | None = None,
    sort_by: str = "updated_at",
    order: str = "desc",
):
    """List all literature with optional filtering."""
    conn = get_connection()

    query = "SELECT * FROM literature"
    params: list = []

    if tag:
        query += f" WHERE {tag_filter_clause()}"
        params.append(tag)

    valid_sorts = {"title", "year", "created_at", "updated_at", "imported_at", "cite_key"}
    if sort_by not in valid_sorts:
        sort_by = "updated_at"
    order_dir = "DESC" if order == "desc" else "ASC"
    query += f" ORDER BY {sort_by} {order_dir} LIMIT ? OFFSET ?"
    params.extend([limit, skip])

    rows = conn.execute(query, params).fetchall()

    count_query = "SELECT COUNT(*) as c FROM literature"
    count_params: list = []
    if tag:
        count_query += f" WHERE {tag_filter_clause()}"
        count_params.append(tag)
    total = conn.execute(count_query, count_params).fetchone()["c"]

    items = []
    for row in rows:
        item = dict(row)
        item["authors"] = json.loads(item["authors"]) if item["authors"] else []
        item["keywords"] = json.loads(item["keywords"]) if item["keywords"] else []
        item["tags"] = json.loads(item["tags"]) if item["tags"] else []
        item["metadata_sources"] = json.loads(item["metadata_sources"]) if item["metadata_sources"] else {}
        item["search_ready_fts"] = bool(item["search_ready_fts"])
        item["search_ready_vector"] = bool(item["search_ready_vector"])
        item["manually_verified"] = bool(item["manually_verified"])
        if item.get("processing_progress"):
            item["processing_progress"] = json.loads(item["processing_progress"])
        item["full_text_length"] = len(item["full_text"] or "")
        # Don't send full_text in list view
        item.pop("full_text", None)
        items.append(item)

    return {"items": items, "total": total}


@router.get("/{lit_id}")
async def get_literature(lit_id: str):
    """Get a single literature record."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM literature WHERE id = ?", (lit_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Literature not found")

    item = dict(row)
    item["authors"] = json.loads(item["authors"]) if item["authors"] else []
    item["keywords"] = json.loads(item["keywords"]) if item["keywords"] else []
    item["tags"] = json.loads(item["tags"]) if item["tags"] else []
    item["metadata_sources"] = json.loads(item["metadata_sources"]) if item["metadata_sources"] else {}
    item["search_ready_fts"] = bool(item["search_ready_fts"])
    item["search_ready_vector"] = bool(item["search_ready_vector"])
    item["manually_verified"] = bool(item["manually_verified"])
    if item.get("processing_progress"):
        item["processing_progress"] = json.loads(item["processing_progress"])
    item["full_text_length"] = len(item["full_text"] or "")
    # Don't send full_text in default detail view (can be large)
    item.pop("full_text", None)
    return item


@router.get("/{lit_id}/preview")
async def get_literature_preview(lit_id: str):
    """Get preview data for a ready literature item: text snippet, outline, stats."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, title, full_text, file_size, file_path, search_ready_fts, search_ready_vector FROM literature WHERE id = ?",
        (lit_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Literature not found")

    full_text = row["full_text"] or ""

    # Text snippet: first ~800 chars, trimmed to last sentence boundary
    snippet = full_text[:1000].strip()
    if len(full_text) > 1000:
        # Trim to last sentence-ending punctuation
        for sep in ("。", ".", "\n\n", "\n"):
            idx = snippet.rfind(sep)
            if 200 < idx < 1000:
                snippet = snippet[: idx + len(sep)]
                break
        snippet = snippet.rstrip() + "……"

    # Word/char stats
    char_count = len(full_text)
    # For Chinese text, word count ≈ char count; for English, split by whitespace
    word_count = len(full_text.split()) if full_text else 0

    # Page count from PyMuPDF
    page_count = 0
    file_path = row["file_path"]
    if file_path:
        try:
            import pymupdf
            doc = pymupdf.open(file_path)
            page_count = len(doc)
            doc.close()
        except Exception:
            pass

    # Document outline: try PDF bookmarks first, then extract from cached elements
    outline: list[dict] = []
    if file_path:
        try:
            import pymupdf
            doc = pymupdf.open(file_path)
            toc = doc.get_toc(simple=True)  # [[level, title, page], ...]
            doc.close()
            if toc:
                outline = [{"depth": entry[0], "title": entry[1], "page": entry[2]} for entry in toc if entry[1].strip()]
        except Exception:
            pass

    # If no PDF bookmarks, try to extract headings from cached structured elements
    if not outline:
        try:
            from backend.services.extract_cache import load_cached
            file_hash_row = conn.execute("SELECT file_hash FROM literature WHERE id = ?", (lit_id,)).fetchone()
            if file_hash_row and file_hash_row["file_hash"]:
                elements = load_cached(file_hash_row["file_hash"])
                if elements:
                    outline = _extract_headings_from_elements(elements)
        except Exception:
            pass

    return {
        "snippet": snippet,
        "char_count": char_count,
        "word_count": word_count,
        "page_count": page_count,
        "file_size": row["file_size"],
        "search_ready_fts": bool(row["search_ready_fts"]),
        "search_ready_vector": bool(row["search_ready_vector"]),
        "outline": outline,
    }


def _extract_headings_from_elements(elements: list[dict]) -> list[dict]:
    """Extract heading-like lines from structured elements.

    Heuristic: short lines (<80 chars) that look like section headers
    (all caps, numbered sections, common academic headings).
    """
    import re

    ACADEMIC_HEADINGS = {
        "abstract", "introduction", "background", "methods", "methodology",
        "materials and methods", "results", "discussion", "conclusion",
        "conclusions", "references", "acknowledgements", "acknowledgments",
        "supplementary", "appendix", "limitations", "funding",
        "conflict of interest", "conflicts of interest", "data availability",
    }

    headings: list[dict] = []
    seen: set[str] = set()

    for el in elements:
        hl = el.get("heading_level")
        content = (el.get("content") or "").strip()
        if not content or len(content) > 120:
            continue

        is_heading = False
        depth = 1

        if hl and isinstance(hl, int) and hl > 0:
            is_heading = True
            depth = hl
        elif el.get("type") in ("heading", "title", "section_header"):
            is_heading = True
        elif len(content) < 80:
            lower = content.lower().rstrip(".:：。")
            # Check common academic headings
            if lower in ACADEMIC_HEADINGS:
                is_heading = True
            # Check numbered sections like "1.", "1.1", "2.1.3", "Chapter 1"
            elif re.match(r"^(\d+\.)+\s*\S", content) or re.match(r"^(chapter|section|part)\s+\d", lower):
                is_heading = True
                # Depth from number of dots: "1." = 1, "1.1" = 2, "1.1.1" = 3
                dots = content.split()[0].count(".")
                depth = max(1, dots)
            # Chinese section markers
            elif re.match(r"^[第一二三四五六七八九十百]+[章节部篇]", content):
                is_heading = True

        if is_heading:
            key = content[:60].lower()
            if key not in seen:
                seen.add(key)
                headings.append({
                    "depth": depth,
                    "title": content,
                    "page": el.get("page_number", 0),
                })

    return headings


@router.post("")
async def create_literature(data: LiteratureCreate):
    """Manually create a literature record."""
    conn = get_connection()

    existing_keys = {
        r["cite_key"] for r in conn.execute("SELECT cite_key FROM literature").fetchall()
    }

    from backend.services.metadata import generate_cite_key
    authors_dicts = [a.model_dump() for a in data.authors]
    cite_key = generate_cite_key(authors_dicts, data.year, existing_keys, title=data.title)

    now = datetime.now().isoformat()
    lit_id = str(uuid.uuid4())

    conn.execute(
        """INSERT INTO literature (id, cite_key, title, authors, abstract, journal, publisher,
           volume, issue, pages, year, date, doi, pmid, pmcid, issn, isbn,
           type, keywords, tags, language, metadata_sources, metadata_confidence,
           manually_verified, processing_status, processing_error, search_ready_fts,
           search_ready_vector, created_at, updated_at, imported_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            lit_id, cite_key, data.title,
            json.dumps([a.model_dump() for a in data.authors]),
            data.abstract, data.journal, data.publisher,
            data.volume, data.issue, data.pages, data.year, data.date,
            data.doi, data.pmid, data.pmcid, data.issn, data.isbn,
            data.type.value, json.dumps(data.keywords), json.dumps(data.tags),
            data.language, json.dumps({"all": "manual"}), 0.5, 0,
            "partial", None, 0, 0,
            now, now, now,
        ),
    )
    conn.commit()

    return {"id": lit_id, "cite_key": cite_key}


@router.put("/{lit_id}")
async def update_literature(lit_id: str, data: LiteratureUpdate):
    """Update a literature record."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM literature WHERE id = ?", (lit_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Literature not found")

    updates = {}
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "authors":
            if value is not None:
                updates["authors"] = json.dumps([a.model_dump() if hasattr(a, 'model_dump') else a for a in value])
        elif field in ("keywords", "tags"):
            if value is not None:
                updates[field] = json.dumps(value)
        elif field == "type":
            if value is not None:
                updates[field] = value.value if hasattr(value, 'value') else value
        elif field == "manually_verified":
            if value is not None:
                updates[field] = int(bool(value))
        else:
            updates[field] = value

    if not updates:
        return {"ok": True}

    updates["updated_at"] = datetime.now().isoformat()

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [lit_id]
    conn.execute(f"UPDATE literature SET {set_clause} WHERE id = ?", values)
    conn.commit()

    # Re-index if title or abstract changed
    if "title" in updates or "abstract" in updates:
        current = conn.execute("SELECT title, abstract, full_text FROM literature WHERE id = ?", (lit_id,)).fetchone()
        await index_literature(lit_id, current["title"], current["abstract"], current["full_text"])

    return {"ok": True}


@router.delete("/{lit_id}")
async def delete_literature(lit_id: str):
    """Delete a literature record and its indexes."""
    conn = get_connection()
    row = conn.execute("SELECT id FROM literature WHERE id = ?", (lit_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Literature not found")

    conn.execute("DELETE FROM literature WHERE id = ?", (lit_id,))
    conn.execute("DELETE FROM literature_fts WHERE literature_id = ?", (lit_id,))
    conn.execute("DELETE FROM citation WHERE literature_id = ?", (lit_id,))
    conn.commit()

    await remove_index(lit_id)

    # Clean up document tree
    from backend.services.doc_tree_cache import delete_tree as delete_doc_tree
    delete_doc_tree(lit_id)

    return {"ok": True}


# =====================
# Background extraction pipeline (Phase B) — subprocess-isolated
# =====================

# Track active extraction processes: {lit_id: multiprocessing.Process}
_active_extractions: dict[str, "multiprocessing.Process"] = {}


def _launch_extraction_subprocess(
    lit_id: str, file_path: Path, file_hash: str, is_scanned: bool,
    skip_ocr: bool = False, retry_count: int = 0,
):
    """Launch extraction in an isolated subprocess.

    If the subprocess crashes (segfault, OOM), the main server stays alive.
    A watchdog task monitors the process and handles retries.
    """
    import multiprocessing

    from backend.services.extraction_worker import run_extraction

    proc = multiprocessing.Process(
        target=run_extraction,
        args=(lit_id, str(file_path), file_hash, is_scanned, skip_ocr),
        daemon=True,
        name=f"extract-{lit_id[:8]}",
    )
    proc.start()
    _active_extractions[lit_id] = proc
    logger.info("Extraction subprocess started: pid=%d for %s (retry=%d, skip_ocr=%s)",
                proc.pid, file_path.name, retry_count, skip_ocr)

    # Schedule watchdog
    asyncio.get_event_loop().create_task(
        _watch_extraction(lit_id, file_path, file_hash, is_scanned, proc, retry_count)
    )


async def _watch_extraction(
    lit_id: str, file_path: Path, file_hash: str, is_scanned: bool,
    proc, retry_count: int,
):
    """Monitor extraction subprocess. On crash, mark failed and auto-retry once."""
    MAX_RETRIES = 1

    while proc.is_alive():
        await asyncio.sleep(2)

    exitcode = proc.exitcode
    _active_extractions.pop(lit_id, None)

    if exitcode == 0:
        logger.info("Extraction subprocess completed successfully for %s", lit_id[:12])
        return

    # Non-zero exit → Python exception (1) or crash/signal (negative = signal number)
    if exitcode is not None and exitcode < 0:
        import signal
        sig_name = "unknown"
        try:
            sig_name = signal.Signals(-exitcode).name
        except (ValueError, AttributeError):
            sig_name = str(-exitcode)
        error_msg = f"Processing crashed (signal {sig_name}). This usually means the file is too large or complex for OCR."
    else:
        error_msg = "Processing failed with an internal error. Check server logs for details."

    logger.error("Extraction subprocess exited %d for %s: %s", exitcode or -1, lit_id[:12], error_msg)

    conn = get_connection()

    if retry_count < MAX_RETRIES:
        # Auto-retry with degraded settings
        retry_msg = f"{error_msg} Auto-retrying with simplified processing..."
        conn.execute(
            """UPDATE literature SET processing_error = ?, processing_progress = NULL, updated_at = ?
               WHERE id = ?""",
            (retry_msg, datetime.now().isoformat(), lit_id),
        )
        conn.commit()
        logger.info("Auto-retrying extraction for %s (attempt %d, skip_ocr=True)", lit_id[:12], retry_count + 1)

        # Retry: skip OCR (most common crash source), use only PyMuPDF
        _launch_extraction_subprocess(
            lit_id, file_path, file_hash, is_scanned,
            skip_ocr=True, retry_count=retry_count + 1,
        )
    else:
        # All retries exhausted
        conn.execute(
            """UPDATE literature SET processing_status = 'failed', processing_error = ?,
               processing_progress = NULL, updated_at = ? WHERE id = ?""",
            (error_msg, datetime.now().isoformat(), lit_id),
        )
        conn.commit()
        logger.error("All retries exhausted for %s", lit_id[:12])


# =====================
# Retry processing
# =====================

@router.post("/{lit_id}/retry")
async def retry_processing(lit_id: str):
    """Retry background extraction for a failed or stuck literature item."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, file_path, file_hash, processing_status FROM literature WHERE id = ?",
        (lit_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Literature not found")

    file_path = Path(row["file_path"])
    if not file_path.exists():
        raise HTTPException(400, "Original PDF file not found on disk")

    from backend.services.ocr_extractor import is_scanned_pdf
    is_scanned = is_scanned_pdf(file_path)

    # Reset status
    conn.execute(
        """UPDATE literature SET processing_status = 'processing', processing_error = NULL,
           processing_progress = NULL, updated_at = ? WHERE id = ?""",
        (datetime.now().isoformat(), lit_id),
    )
    conn.commit()

    _launch_extraction_subprocess(lit_id, file_path, row["file_hash"], is_scanned)

    return {"ok": True, "message": "Reprocessing started"}


# =====================
# Import endpoint
# =====================

@router.post("/import/pdf")
async def import_pdf(file: UploadFile = File(...)):
    """Import a PDF file.

    Phase A (synchronous, <3s): Save file, extract metadata (hash, DOI, CrossRef), create DB record.
    Phase B (background): Full text extraction (ODL/PyMuPDF/OCR), indexing, tree building.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    # Save uploaded file
    dest = FILES_DIR / file.filename
    counter = 1
    while dest.exists():
        stem = Path(file.filename).stem
        dest = FILES_DIR / f"{stem}_{counter}.pdf"
        counter += 1

    try:
        with open(dest, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(500, f"Failed to save file: {e}")

    # Get existing keys and hashes
    conn = get_connection()
    existing_keys = {
        r["cite_key"] for r in conn.execute("SELECT cite_key FROM literature").fetchall()
    }
    existing_hashes = {
        r["file_hash"]
        for r in conn.execute("SELECT file_hash FROM literature WHERE file_hash IS NOT NULL").fetchall()
    }

    # Phase A: Fast metadata extraction (<3s)
    try:
        result = await process_pdf_metadata(dest, existing_keys, existing_hashes)
    except Exception as e:
        dest.unlink(missing_ok=True)
        logger.exception("Phase A metadata extraction failed for %s", file.filename)
        raise HTTPException(500, f"Metadata extraction failed: {e}")

    if result is None:
        dest.unlink(missing_ok=True)
        raise HTTPException(409, "Duplicate file or processing failed")

    lit = result.literature

    # Save to database immediately (with empty full_text — Phase B fills it)
    try:
        conn.execute(
            """INSERT INTO literature (id, cite_key, title, authors, abstract, journal, publisher,
               volume, issue, pages, year, date, doi, pmid, pmcid, issn, isbn,
               type, keywords, tags, language, file_path, file_hash, file_size, full_text,
               processing_status, processing_error, search_ready_fts, search_ready_vector,
               metadata_sources, metadata_confidence, manually_verified,
               created_at, updated_at, imported_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                lit.id, lit.cite_key, lit.title,
                json.dumps([a.model_dump() for a in lit.authors]),
                lit.abstract, lit.journal, lit.publisher,
                lit.volume, lit.issue, lit.pages, lit.year, lit.date,
                lit.doi, lit.pmid, lit.pmcid, lit.issn, lit.isbn,
                lit.type.value if hasattr(lit.type, 'value') else lit.type,
                json.dumps(lit.keywords), json.dumps(lit.tags), lit.language,
                str(dest), lit.file_hash, lit.file_size, lit.full_text,
                "processing", None, 0, 0,
                json.dumps(lit.metadata_sources), lit.metadata_confidence, 0,
                lit.created_at.isoformat(), lit.updated_at.isoformat(), lit.imported_at.isoformat(),
            ),
        )
        conn.commit()
    except Exception as e:
        dest.unlink(missing_ok=True)
        logger.exception("Failed to save literature record for %s", file.filename)
        raise HTTPException(500, f"Database error: {e}")

    # Phase B: Schedule background extraction + indexing
    logger.info(
        "Import Phase A done for '%s' [%s]. Scheduling background extraction (scanned=%s).",
        lit.title[:50], lit.cite_key, result.is_scanned,
    )
    _launch_extraction_subprocess(lit.id, dest, lit.file_hash, result.is_scanned)

    return {
        "id": lit.id,
        "cite_key": lit.cite_key,
        "title": lit.title,
        "confidence": lit.metadata_confidence,
        "processing_status": "processing",
        "message": "Metadata imported. Full-text extraction and indexing are still running.",
    }


# =====================
# Batch re-extraction & re-indexing
# =====================

@router.post("/reindex-all")
async def reindex_all():
    """Re-extract and re-index all literature entries.

    1. Fill missing full_text from cache or PyMuPDF extraction
    2. Rebuild FTS5 index for all entries
    3. Rebuild vector index (ChromaDB) for all entries with structured elements
    4. Build document trees for entries that don't have them
    """
    from backend.services.extract_cache import load_cached, save_cache
    from backend.services.metadata import _detect_language
    from backend.services.pdf_extractor import pymupdf_extract_structured
    from backend.services.structured_extractor import extract_structured

    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, abstract, file_hash, file_path, full_text FROM literature WHERE file_hash IS NOT NULL"
    ).fetchall()

    stats = {"total": len(rows), "filled": 0, "indexed_fts": 0, "indexed_vector": 0, "skipped": 0, "errors": 0}

    for row in rows:
        lit_id = row["id"]
        title = row["title"]
        abstract = row["abstract"]
        file_hash = row["file_hash"]
        file_path = Path(row["file_path"]) if row["file_path"] else None
        has_text = row["full_text"] and len(row["full_text"]) > 10

        # Get or create structured elements
        elements = load_cached(file_hash) if file_hash else None

        if not elements and file_path and file_path.exists():
            try:
                from backend.services.ocr_extractor import is_scanned_pdf, ocr_extract_structured
                if is_scanned_pdf(file_path):
                    elements = ocr_extract_structured(file_path)
                else:
                    quick_elements = pymupdf_extract_structured(file_path)
                    elements = extract_structured(file_path, quick_elements=quick_elements)
                if elements:
                    save_cache(file_hash, elements)
            except Exception as e:
                logger.warning("Extraction failed for %s: %s", lit_id[:12], e)
                conn.execute(
                    """
                    UPDATE literature
                    SET processing_status = 'failed', processing_error = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (str(e), datetime.now().isoformat(), lit_id),
                )
                conn.commit()
                stats["errors"] += 1
                continue

        # Fill missing full_text
        vector_chunk_count = 0

        if not has_text and elements:
            full_text = "\n\n".join(el["content"] for el in elements)
            language = _detect_language(full_text[:500])
            conn.execute(
                "UPDATE literature SET full_text = ?, language = ?, updated_at = ? WHERE id = ?",
                (full_text, language, datetime.now().isoformat(), lit_id),
            )
            conn.commit()
            stats["filled"] += 1
            has_text = True
            # Build doc tree
            _auto_build_doc_tree(lit_id, title, elements)

        if not has_text and not elements:
            conn.execute(
                """
                UPDATE literature
                SET processing_status = 'partial', processing_error = NULL,
                    search_ready_fts = 0, search_ready_vector = 0, updated_at = ?
                WHERE id = ?
                """,
                (datetime.now().isoformat(), lit_id),
            )
            conn.commit()
            stats["skipped"] += 1
            continue

        # Re-read full_text for FTS indexing
        current = conn.execute(
            "SELECT title, abstract, full_text FROM literature WHERE id = ?", (lit_id,)
        ).fetchone()

        # FTS5 index
        if current:
            sqlite.index_literature_fts(
                lit_id, current["title"], current["abstract"], current["full_text"]
            )
            stats["indexed_fts"] += 1

        # Vector index (needs structured elements)
        if elements:
            try:
                vector_chunk_count = await index_literature(
                    lit_id, title, abstract, current["full_text"] if current else "",
                    structured_elements=elements,
                )
                if vector_chunk_count > 0:
                    stats["indexed_vector"] += 1
            except Exception as e:
                logger.warning("Vector indexing failed for %s: %s", lit_id[:12], e)

        status = "ready" if has_text and vector_chunk_count > 0 else "partial"
        conn.execute(
            """
            UPDATE literature
            SET processing_status = ?, processing_error = NULL,
                search_ready_fts = ?, search_ready_vector = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                int(current is not None),
                int(vector_chunk_count > 0),
                datetime.now().isoformat(),
                lit_id,
            ),
        )
        conn.commit()

    return stats


# =====================
# Tags
# =====================

@router.get("/{lit_id}/tags")
async def get_tags(lit_id: str):
    """Get tags for a literature record."""
    conn = get_connection()
    row = conn.execute("SELECT tags FROM literature WHERE id = ?", (lit_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Literature not found")
    return json.loads(row["tags"]) if row["tags"] else []


@router.get("/tags/all")
async def list_all_tags():
    """List all unique tags across all literature."""
    conn = get_connection()
    rows = conn.execute("SELECT tags FROM literature").fetchall()
    all_tags = set()
    for row in rows:
        tags = json.loads(row["tags"]) if row["tags"] else []
        all_tags.update(tags)
    return sorted(all_tags)


@router.post("/regenerate-cite-keys")
async def regenerate_cite_keys():
    """Regenerate all cite keys using the title-primary strategy."""
    from backend.services.metadata import generate_cite_key

    conn = get_connection()
    all_rows = conn.execute(
        "SELECT id, cite_key, title, authors, year FROM literature ORDER BY created_at"
    ).fetchall()

    existing_keys: set[str] = set()
    updated = []
    for r in all_rows:
        authors = json.loads(r["authors"]) if r["authors"] else []
        new_key = generate_cite_key(authors, r["year"], existing_keys, title=r["title"] or "")
        existing_keys.add(new_key)
        if new_key != r["cite_key"]:
            conn.execute(
                "UPDATE literature SET cite_key = ?, updated_at = ? WHERE id = ?",
                (new_key, datetime.now().isoformat(), r["id"]),
            )
            updated.append({"id": r["id"], "old": r["cite_key"], "new": new_key})

    conn.commit()
    return {"updated": updated, "count": len(updated)}
