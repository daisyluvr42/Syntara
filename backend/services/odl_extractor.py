"""PDF structured extraction using opendataloader-pdf.

Provides high-accuracy structured parsing: paragraphs, headings, tables, lists,
captions — each with page numbers, bounding boxes, and element types.
Also handles OCR for scanned PDFs natively.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Callable

import opendataloader_pdf

from backend.config import ODL_FORMAT, ODL_MODE, ODL_OUTPUT_DIR


# Element types we index (skip header_footer and image)
_INDEXABLE_TYPES = {"paragraph", "heading", "caption", "table", "text_block", "list"}


def extract_structured(
    file_path: str | Path,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[dict]:
    """
    Extract structured elements from a PDF via opendataloader-pdf.

    Returns a list of element dicts sorted by document order, each containing:
      - type: str (paragraph, heading, table, list, caption, text_block)
      - content: str
      - page_number: int
      - bbox: list[float] | None  ([x0, y0, x1, y1])
      - heading_level: int | None (for headings only)
    """
    file_path = Path(file_path)

    # Unique output subdir keyed by filename + uuid to avoid collisions
    out_dir = ODL_OUTPUT_DIR / f"{file_path.stem}_{uuid.uuid4().hex[:8]}"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        if progress_callback:
            progress_callback(0, 1)  # Starting

        # Call opendataloader-pdf (blocking JVM call)
        convert_kwargs: dict = {
            "input_path": str(file_path),
            "output_dir": str(out_dir),
            "format": ODL_FORMAT,
        }
        if ODL_MODE == "hybrid":
            convert_kwargs["hybrid"] = "docling-fast"

        opendataloader_pdf.convert(**convert_kwargs)

        # Read output JSON
        json_files = list(out_dir.glob("*.json"))
        if not json_files:
            raise FileNotFoundError(f"opendataloader-pdf produced no JSON output for {file_path}")

        raw_elements = json.loads(json_files[0].read_text(encoding="utf-8"))
        if isinstance(raw_elements, dict):
            raw_elements = raw_elements.get("elements", [])

        # Parse into normalized element list
        elements = []
        for el in raw_elements:
            el_type = el.get("type", "paragraph")
            if el_type not in _INDEXABLE_TYPES:
                continue

            content = el.get("content", "") or el.get("text", "")
            if not content or not content.strip():
                continue

            elements.append({
                "type": el_type,
                "content": content.strip(),
                "page_number": el.get("page_number") or el.get("page", 0),
                "bbox": el.get("bounding_box") or el.get("bbox"),
                "heading_level": el.get("level") if el_type == "heading" else None,
            })

        if progress_callback:
            progress_callback(1, 1)  # Done

        return elements

    finally:
        # Clean up output directory
        import shutil
        shutil.rmtree(out_dir, ignore_errors=True)


async def extract_structured_async(file_path: str | Path) -> list[dict]:
    """Async wrapper: runs the blocking JVM extraction in a thread pool."""
    return await asyncio.to_thread(extract_structured, file_path)


def extract_full_text(file_path: str | Path) -> str:
    """Extract full plain text from PDF. Uses structured extraction internally."""
    elements = extract_structured(file_path)
    return "\n\n".join(el["content"] for el in elements)


async def extract_full_text_async(file_path: str | Path) -> str:
    """Async wrapper for full text extraction."""
    return await asyncio.to_thread(extract_full_text, file_path)


def build_structured_chunks(
    elements: list[dict],
    chunk_size: int = 500,
    overlap_words: int = 50,
) -> list[dict]:
    """
    Build semantically-aware chunks from structured elements.

    Strategy:
    - Headings and tables are always their own chunks (never split or merged).
    - Paragraphs, text_blocks, lists, and captions accumulate until chunk_size.
    - Each chunk carries its nearest preceding heading as context.
    """
    chunks: list[dict] = []
    current_heading = ""
    buffer = ""
    buffer_page = 0
    buffer_type = "paragraph"
    idx = 0

    def _flush():
        nonlocal buffer, idx
        if buffer.strip():
            chunks.append({
                "content": buffer.strip(),
                "chunk_index": idx,
                "element_type": buffer_type,
                "heading": current_heading,
                "page_number": buffer_page,
            })
            idx += 1
            buffer = ""

    for el in elements:
        el_type = el["type"]
        content = el["content"]

        if el_type == "heading":
            # Flush any accumulated buffer before starting a new section
            _flush()
            current_heading = content
            # Heading itself is a standalone chunk
            chunks.append({
                "content": content,
                "chunk_index": idx,
                "element_type": "heading",
                "heading": content,
                "page_number": el.get("page_number", 0),
            })
            idx += 1
            continue

        if el_type == "table":
            # Tables are always standalone — never merged with prose
            _flush()
            chunks.append({
                "content": content,
                "chunk_index": idx,
                "element_type": "table",
                "heading": current_heading,
                "page_number": el.get("page_number", 0),
            })
            idx += 1
            continue

        # Accumulate paragraph / text_block / list / caption
        if not buffer:
            buffer = content
            buffer_page = el.get("page_number", 0)
            buffer_type = el_type
        elif len(buffer) + len(content) > chunk_size:
            _flush()
            # Overlap: carry the last N words into the next buffer
            words = content.split()
            buffer = content
            buffer_page = el.get("page_number", 0)
            buffer_type = el_type
        else:
            buffer = buffer + "\n" + content

    # Flush remaining
    _flush()

    return chunks
