"""Structured PDF extraction using LiteParse.

LiteParse is the default local structured parser for text-based PDFs. It avoids
the JVM startup cost of opendataloader-pdf while still preserving page order and
basic spatial information.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from backend.config import (
    LITEPARSE_DPI,
    LITEPARSE_MAX_PAGES,
    LITEPARSE_NUM_WORKERS,
    LITEPARSE_OCR_LANGUAGE,
    LITEPARSE_OCR_SERVER_URL,
)


def extract_structured(
    file_path: str | Path,
    *,
    use_ocr: bool = False,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[dict]:
    """Extract normalized structured elements from a PDF via LiteParse."""
    from liteparse import LiteParse

    if progress_callback:
        progress_callback(0, 1)

    parser = LiteParse(
        ocr_enabled=bool(use_ocr),
        ocr_language=LITEPARSE_OCR_LANGUAGE,
        ocr_server_url=LITEPARSE_OCR_SERVER_URL or None,
        max_pages=LITEPARSE_MAX_PAGES,
        dpi=LITEPARSE_DPI,
        quiet=True,
        num_workers=LITEPARSE_NUM_WORKERS,
    )
    result = parser.parse(str(file_path))

    elements: list[dict] = []
    for page in result.pages:
        page_num = getattr(page, "page_num", 0) or getattr(page, "pageNum", 0)
        paragraphs = _split_page_text(getattr(page, "text", "") or "")
        page_bbox = _page_bbox(getattr(page, "text_items", None) or getattr(page, "textItems", None) or [])

        for para in paragraphs:
            el_type, heading_level = _classify_text(para)
            elements.append({
                "type": el_type,
                "content": para,
                "page_number": page_num,
                "bbox": page_bbox,
                "heading_level": heading_level,
            })

    if progress_callback:
        progress_callback(1, 1)

    return elements


def _split_page_text(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    chunks = re.split(r"\n\s*\n+", text)
    paragraphs: list[str] = []
    for chunk in chunks:
        lines = [re.sub(r"\s+", " ", line).strip() for line in chunk.splitlines()]
        lines = [line for line in lines if line]
        if not lines:
            continue
        paragraphs.append("\n".join(lines))
    return paragraphs


def _page_bbox(items: list) -> list[float] | None:
    boxes = []
    for item in items:
        x = getattr(item, "x", None)
        y = getattr(item, "y", None)
        width = getattr(item, "width", None)
        height = getattr(item, "height", None)
        if None in (x, y, width, height):
            continue
        boxes.append((float(x), float(y), float(x + width), float(y + height)))

    if not boxes:
        return None

    return [
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    ]


def _classify_text(text: str) -> tuple[str, int | None]:
    first = text.splitlines()[0].strip()
    if (
        len(text.splitlines()) <= 2
        and len(first) < 120
        and first
        and not first.endswith((".", ",", ";", ":", "。", "，"))
    ):
        m = re.match(r"^(\d+(?:\.\d+)*)\s+\S", first)
        if m:
            return "heading", min(m.group(1).count(".") + 1, 4)
        if first.isupper() and len(first) < 80:
            return "heading", 1
    return "paragraph", None
