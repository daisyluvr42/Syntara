"""Extract cache management API router."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from backend.config import EXTRACT_CACHE_DIR
from backend.db.sqlite import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/extract-cache", tags=["extract-cache"])


def _detect_source_type(elements: list[dict]) -> str:
    """Heuristic to detect whether cache came from PaddleOCR or ODL."""
    if not elements:
        return "unknown"
    sample = elements[0]
    # PaddleOCR results typically have 'text' + 'confidence' / 'bbox' keys
    if "confidence" in sample or "bbox" in sample:
        return "paddleocr"
    # ODL results typically have 'type' + 'metadata' keys
    if "type" in sample and "metadata" in sample:
        return "odl"
    # Fallback: check for common ODL element types
    if sample.get("type") in ("Title", "NarrativeText", "Table", "Image", "ListItem"):
        return "odl"
    return "paddleocr"


def _lookup_file_info(file_hash: str) -> dict:
    """Look up human-readable file name and title from literature or corpus table."""
    conn = get_connection()
    # Try literature table first
    row = conn.execute(
        "SELECT file_path, title FROM literature WHERE file_hash = ?",
        (file_hash,),
    ).fetchone()
    if row:
        file_path = row["file_path"] or ""
        return {
            "file_name": Path(file_path).name if file_path else "",
            "title": row["title"] or "",
        }
    # Try corpus table
    row = conn.execute(
        "SELECT file_path, title FROM corpus WHERE file_hash = ?",
        (file_hash,),
    ).fetchone()
    if row:
        file_path = row["file_path"] or ""
        return {
            "file_name": Path(file_path).name if file_path else "",
            "title": row["title"] or "",
        }
    return {"file_name": "", "title": ""}


def _build_cache_item(cache_path: Path) -> dict | None:
    """Build a cache item dict from a cache JSON file."""
    if not cache_path.suffix == ".json":
        return None
    file_hash = cache_path.stem
    try:
        stat = cache_path.stat()
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    info = _lookup_file_info(file_hash)
    return {
        "file_hash": file_hash,
        "file_name": info["file_name"],
        "title": info["title"],
        "source_type": _detect_source_type(data),
        "element_count": len(data),
        "file_size_kb": round(stat.st_size / 1024, 1),
        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


@router.get("/stats")
async def get_stats():
    """Get cache statistics."""
    items: list[dict] = []
    if EXTRACT_CACHE_DIR.exists():
        for p in EXTRACT_CACHE_DIR.glob("*.json"):
            item = _build_cache_item(p)
            if item:
                items.append(item)

    total_size_kb = sum(i["file_size_kb"] for i in items)
    by_source: dict[str, int] = {}
    for i in items:
        src = i["source_type"]
        by_source[src] = by_source.get(src, 0) + 1

    return {
        "total_items": len(items),
        "total_size_kb": round(total_size_kb, 1),
        "by_source": by_source,
    }


@router.get("/{file_hash}")
async def get_cache_detail(file_hash: str):
    """Get details of a cached extraction."""
    cache_path = EXTRACT_CACHE_DIR / f"{file_hash}.json"
    if not cache_path.exists():
        raise HTTPException(404, "Cache entry not found")

    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(500, f"Failed to read cache file: {exc}")

    stat = cache_path.stat()
    info = _lookup_file_info(file_hash)

    # Compute total text length across all elements
    total_text_length = 0
    for el in data:
        text = el.get("text", "") or el.get("content", "")
        total_text_length += len(text)

    return {
        "file_hash": file_hash,
        "file_name": info["file_name"],
        "title": info["title"],
        "source_type": _detect_source_type(data),
        "element_count": len(data),
        "file_size_kb": round(stat.st_size / 1024, 1),
        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "elements": data[:50],
        "total_text_length": total_text_length,
    }


@router.get("")
async def list_cache():
    """List all cached extractions."""
    items: list[dict] = []
    if EXTRACT_CACHE_DIR.exists():
        for p in sorted(EXTRACT_CACHE_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            item = _build_cache_item(p)
            if item:
                items.append(item)

    return {"items": items}


@router.delete("/{file_hash}")
async def delete_cache_entry(file_hash: str):
    """Delete a single cache entry."""
    cache_path = EXTRACT_CACHE_DIR / f"{file_hash}.json"
    if not cache_path.exists():
        raise HTTPException(404, "Cache entry not found")
    cache_path.unlink()
    logger.info("Deleted extract cache: %s", file_hash[:12])
    return {"ok": True}


@router.delete("")
async def clear_cache(all: bool = Query(False)):
    """Clear entire cache (requires ?all=true)."""
    if not all:
        raise HTTPException(400, "Pass ?all=true to confirm clearing the entire cache")

    deleted = 0
    if EXTRACT_CACHE_DIR.exists():
        for p in EXTRACT_CACHE_DIR.glob("*.json"):
            p.unlink()
            deleted += 1

    logger.info("Cleared extract cache: %d files deleted", deleted)
    return {"ok": True, "deleted": deleted}
