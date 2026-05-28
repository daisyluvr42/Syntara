"""Persistent cache for PDF extraction results (OCR / ODL structured elements).

Cache keyed by file_hash, stored as JSON in data/extract_cache/.
Avoids re-running expensive OCR or ODL extraction on repeat operations.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from backend.config import EXTRACT_CACHE_DIR

logger = logging.getLogger(__name__)


def _cache_path(file_hash: str) -> Path:
    """Return the cache file path for a given file hash."""
    return EXTRACT_CACHE_DIR / f"{file_hash}.json"


def load_cached(file_hash: str) -> list[dict] | None:
    """Load cached structured elements for a file hash. Returns None on miss or empty."""
    path = _cache_path(file_hash)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not data:
            # Empty cache is useless — treat as miss and remove the bad file
            logger.warning("Extract cache empty for %s, removing", file_hash[:12])
            path.unlink(missing_ok=True)
            return None
        logger.info("Extract cache hit: %s (%d elements)", file_hash[:12], len(data))
        return data
    except (json.JSONDecodeError, OSError):
        logger.warning("Extract cache corrupted for %s, removing", file_hash[:12])
        path.unlink(missing_ok=True)
        return None


def save_cache(file_hash: str, elements: list[dict]) -> None:
    """Persist structured elements to cache. Refuses to save empty results."""
    if not elements:
        logger.warning("Refusing to cache empty extraction for %s", file_hash[:12])
        return
    path = _cache_path(file_hash)
    path.write_text(json.dumps(elements, ensure_ascii=False), encoding="utf-8")
    logger.info("Extract cache saved: %s (%d elements, %.1f KB)",
                file_hash[:12], len(elements), path.stat().st_size / 1024)


def has_cache(file_hash: str) -> bool:
    """Check if cache exists for a file hash."""
    return _cache_path(file_hash).exists()


def delete_cache(file_hash: str) -> None:
    """Delete cache for a file hash."""
    path = _cache_path(file_hash)
    path.unlink(missing_ok=True)
