"""Subprocess-based extraction worker.

Runs heavy PDF extraction (PyMuPDF / OCR / ODL) in an isolated subprocess
so that crashes (segfault, OOM) don't bring down the main API server.

Communication is via SQLite writes (progress, status) + extract_cache files.
"""

from __future__ import annotations

import asyncio
import gc
import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _db_path() -> str:
    from backend.config import DATA_DIR
    return str(DATA_DIR / "syntara.db")


def _update_progress(db: str, lit_id: str, stage: str, current: int, total: int):
    conn = sqlite3.connect(db)
    conn.execute(
        "UPDATE literature SET processing_progress = ?, updated_at = ? WHERE id = ?",
        (json.dumps({"stage": stage, "current": current, "total": total}),
         datetime.now().isoformat(), lit_id),
    )
    conn.commit()
    conn.close()


def _db_update(db: str, lit_id: str, **fields):
    conn = sqlite3.connect(db)
    fields["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE literature SET {set_clause} WHERE id = ?",
                 [*fields.values(), lit_id])
    conn.commit()
    conn.close()


# ── subprocess entry point ──────────────────────────────────────────

def run_extraction(
    lit_id: str,
    file_path_str: str,
    file_hash: str,
    is_scanned: bool,
    skip_ocr: bool = False,
):
    """Run in a subprocess. Exit 0 = ok, 1 = Python exception, other = crash."""
    logging.basicConfig(
        level=logging.INFO,
        format="[worker %(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    file_path = Path(file_path_str)
    db = _db_path()

    # ── Tier 1: PyMuPDF quick text ─────────────────────────────────
    try:
        _update_progress(db, lit_id, "text_extract", 0, 1)
        logger.info("Tier 1 start: %s", file_path.name)

        from backend.services.pdf_extractor import pymupdf_extract_structured
        quick_elements = pymupdf_extract_structured(file_path)
        quick_text = "\n\n".join(el["content"] for el in quick_elements)
        gc.collect()

        if quick_text.strip():
            from backend.services.metadata import _detect_language
            lang = _detect_language(quick_text[:500])

            conn = sqlite3.connect(db)
            conn.execute(
                "UPDATE literature SET full_text=?, language=?, updated_at=? WHERE id=?",
                (quick_text, lang, datetime.now().isoformat(), lit_id),
            )
            conn.commit()

            # FTS index
            from backend.db import sqlite as sqmod
            row = conn.execute("SELECT title, abstract FROM literature WHERE id=?", (lit_id,)).fetchone()
            if row:
                sqmod.index_literature_fts(lit_id, row[0], row[1], quick_text)
                conn.execute(
                    "UPDATE literature SET processing_status='partial', search_ready_fts=1, updated_at=? WHERE id=?",
                    (datetime.now().isoformat(), lit_id),
                )
                conn.commit()
            conn.close()

        _update_progress(db, lit_id, "text_extract", 1, 1)
        logger.info("Tier 1 done: %s", file_path.name)
    except Exception:
        logger.exception("Tier 1 failed")
        _db_update(db, lit_id,
                   processing_status="failed",
                   processing_error=f"Text extraction crashed: {_exc_summary()}",
                   processing_progress=None)
        sys.exit(1)

    # ── Tier 2: structured extraction + vector index ───────────────
    try:
        from backend.services.extract_cache import load_cached, save_cache

        structured = load_cached(file_hash)
        size_mb = file_path.stat().st_size / (1024 * 1024)

        if structured is None:
            if is_scanned and not skip_ocr:
                from backend.services.ocr_extractor import ocr_extract_structured
                _update_progress(db, lit_id, "ocr", 0, 1)
                logger.info("Tier 2: OCR %s (%.0f MB)", file_path.name, size_mb)
                structured = ocr_extract_structured(
                    file_path,
                    progress_callback=lambda c, t: _update_progress(db, lit_id, "ocr", c, t),
                )
            elif size_mb > 100:
                logger.info("Tier 2: large file, reusing PyMuPDF elements")
                _update_progress(db, lit_id, "structure_extract", 1, 1)
                structured = quick_elements
            else:
                try:
                    from backend.services.odl_extractor import extract_structured
                    _update_progress(db, lit_id, "structure_extract", 0, 1)
                    logger.info("Tier 2: ODL %s (%.0f MB)", file_path.name, size_mb)
                    structured = extract_structured(file_path)
                    _update_progress(db, lit_id, "structure_extract", 1, 1)
                except Exception as e:
                    logger.warning("ODL failed: %s — using PyMuPDF", e)
                    structured = quick_elements

            save_cache(file_hash, structured)

        gc.collect()

        # Update full_text
        full_text = "\n\n".join(el["content"] for el in structured)
        conn = sqlite3.connect(db)
        if full_text.strip():
            from backend.services.metadata import _detect_language
            lang = _detect_language(full_text[:500])
            conn.execute(
                "UPDATE literature SET full_text=?, language=?, updated_at=? WHERE id=?",
                (full_text, lang, datetime.now().isoformat(), lit_id),
            )
            conn.commit()

        # Vector index (async code → use asyncio.run)
        _update_progress(db, lit_id, "indexing", 0, 1)
        row = conn.execute("SELECT title, abstract FROM literature WHERE id=?", (lit_id,)).fetchone()
        vec_count = 0
        if row:
            from backend.db import sqlite as sqmod
            sqmod.index_literature_fts(lit_id, row[0], row[1], full_text)

            from backend.services.indexer import index_literature
            try:
                vec_count = asyncio.run(
                    index_literature(lit_id, row[0], row[1], full_text,
                                    structured_elements=structured)
                )
            except Exception as e:
                logger.warning("Vector indexing failed (embeddings unavailable?): %s", e)

            conn.execute(
                """UPDATE literature
                   SET processing_status=?, processing_error=NULL,
                       search_ready_fts=1, search_ready_vector=?,
                       processing_progress=NULL, updated_at=?
                   WHERE id=?""",
                ("ready" if vec_count > 0 else "partial",
                 int(vec_count > 0),
                 datetime.now().isoformat(), lit_id),
            )
            conn.commit()
        conn.close()

        # Document tree
        try:
            from backend.services.doc_tree_builder import build_tree
            from backend.services.doc_tree_cache import save_tree
            c2 = sqlite3.connect(db)
            r2 = c2.execute("SELECT title FROM literature WHERE id=?", (lit_id,)).fetchone()
            c2.close()
            tree = build_tree(lit_id, r2[0] if r2 else "", structured)
            save_tree(tree)
        except Exception:
            logger.exception("Doc tree build failed")

        logger.info("Tier 2 done: %d elements, %d vectors", len(structured), vec_count)
        sys.exit(0)

    except Exception:
        logger.exception("Tier 2 failed")
        _db_update(db, lit_id,
                   processing_error=f"Structured extraction failed: {_exc_summary()}",
                   processing_progress=None)
        # Tier 1 already set partial status, keep it
        sys.exit(1)


def _exc_summary() -> str:
    """Short summary of current exception."""
    import traceback
    return traceback.format_exception_only(*sys.exc_info()[:2])[-1].strip()
