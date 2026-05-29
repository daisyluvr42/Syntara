"""Preferred structured extraction router for non-scanned PDFs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from backend.config import PDF_STRUCTURED_ENGINE

logger = logging.getLogger(__name__)


def extract_structured(
    file_path: str | Path,
    *,
    quick_elements: list[dict] | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[dict]:
    """Run the configured structured PDF extractor with conservative fallbacks."""
    file_path = Path(file_path)
    engine = PDF_STRUCTURED_ENGINE.lower()

    if engine == "pymupdf":
        return _quick_or_pymupdf(file_path, quick_elements)

    if engine == "odl":
        return _extract_odl_or_fallback(file_path, quick_elements, progress_callback)

    try:
        from backend.services.liteparse_extractor import extract_structured as liteparse_extract_structured

        elements = liteparse_extract_structured(
            file_path,
            use_ocr=False,
            progress_callback=progress_callback,
        )
        if elements:
            return elements
        logger.warning("LiteParse returned no elements for %s", file_path.name)
    except Exception as e:
        logger.warning("LiteParse failed for %s: %s", file_path.name, e)

    return _extract_odl_or_fallback(file_path, quick_elements, progress_callback)


def _extract_odl_or_fallback(
    file_path: Path,
    quick_elements: list[dict] | None,
    progress_callback: Callable[[int, int], None] | None,
) -> list[dict]:
    try:
        from backend.services.odl_extractor import extract_structured as odl_extract_structured

        elements = odl_extract_structured(file_path, progress_callback=progress_callback)
        if elements:
            return elements
        logger.warning("ODL returned no elements for %s", file_path.name)
    except Exception as e:
        logger.warning("ODL failed for %s: %s", file_path.name, e)

    return _quick_or_pymupdf(file_path, quick_elements)


def _quick_or_pymupdf(file_path: Path, quick_elements: list[dict] | None) -> list[dict]:
    if quick_elements is not None:
        return quick_elements

    from backend.services.pdf_extractor import pymupdf_extract_structured

    return pymupdf_extract_structured(file_path)
