"""OCR extraction for scanned PDFs using PaddleOCR v3.

Converts PDF pages to images, runs PaddleOCR, and returns structured elements
compatible with the same format as odl_extractor.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import gc
import logging
import os
from pathlib import Path
from typing import Callable

import numpy as np
import pymupdf

logger = logging.getLogger(__name__)

# Skip PaddleX model-hoster connectivity check (slow and unnecessary for local use)
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

# Lazy-loaded PaddleOCR engine (heavy init, do it once)
_ocr_engine = None

# Per-page timeout (seconds). Pages that exceed this are skipped.
PAGE_TIMEOUT = 120


def _get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        from paddleocr import PaddleOCR

        _ocr_engine = PaddleOCR(
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="PP-OCRv5_mobile_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    return _ocr_engine


def is_scanned_pdf(file_path: str | Path, sample_pages: int = 3) -> bool:
    """Detect whether a PDF is scanned (image-only) by checking first N pages for text."""
    doc = pymupdf.open(str(file_path))
    pages_to_check = min(sample_pages, len(doc))
    total_text = 0
    for i in range(pages_to_check):
        total_text += len(doc[i].get_text().strip())
    doc.close()
    # If average text per page is less than 50 chars, treat as scanned
    return (total_text / max(pages_to_check, 1)) < 50


def _ocr_single_page(engine, img: np.ndarray) -> dict | None:
    """Run OCR on a single page image. Designed to run in a separate thread with timeout."""
    results = engine.predict(img)
    if not results:
        return None
    return results[0]


def _choose_dpi(file_path: Path) -> int:
    """Choose DPI based on file size. Large files get lower DPI to avoid memory issues."""
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > 200:
        return 100  # Low DPI for very large files
    elif file_size_mb > 50:
        return 120  # Medium DPI
    return 150  # Default


def ocr_extract_structured(
    file_path: str | Path,
    dpi: int | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[dict]:
    """
    Extract structured elements from a scanned PDF using PaddleOCR v3.

    Pipeline:
      1. Render each PDF page as an image via PyMuPDF
      2. Run PaddleOCR predict() on each page image (with per-page timeout)
      3. Group OCR text blocks into paragraph-level elements by vertical proximity

    Returns a list of element dicts with the same schema as odl_extractor:
      - type: str ("paragraph")
      - content: str
      - page_number: int (1-based)
      - bbox: list[float] | None
      - heading_level: None
    """
    file_path = Path(file_path)

    # Auto-choose DPI if not specified
    if dpi is None:
        dpi = _choose_dpi(file_path)

    doc = pymupdf.open(str(file_path))
    engine = _get_ocr_engine()
    total_pages = len(doc)

    elements: list[dict] = []
    zoom = dpi / 72.0
    skipped_pages = 0

    logger.info("OCR starting: %s (%d pages, dpi=%d)", file_path.name, total_pages, dpi)

    # Thread pool for per-page timeout control
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    try:
        for page_idx in range(total_pages):
            if progress_callback:
                progress_callback(page_idx + 1, total_pages)
            if (page_idx + 1) % 10 == 0 or page_idx == 0:
                logger.info("OCR progress: page %d/%d (skipped %d)", page_idx + 1, total_pages, skipped_pages)

            page = doc[page_idx]
            # Render page to pixmap
            mat = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            # Convert to numpy array for PaddleOCR (copy so pixmap can be freed)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3).copy()
            del pix  # Release pixmap memory immediately

            # Run OCR with timeout
            ocr_result = None
            try:
                future = executor.submit(_ocr_single_page, engine, img)
                ocr_result = future.result(timeout=PAGE_TIMEOUT)
            except concurrent.futures.TimeoutError:
                logger.warning("OCR timeout on page %d/%d (>%ds), skipping", page_idx + 1, total_pages, PAGE_TIMEOUT)
                skipped_pages += 1
                # Cancel doesn't actually stop the thread, but we proceed
                future.cancel()
            except Exception as e:
                logger.warning("OCR error on page %d/%d: %s, skipping", page_idx + 1, total_pages, e)
                skipped_pages += 1

            del img  # Release image memory

            if not ocr_result:
                if (page_idx + 1) % 20 == 0:
                    gc.collect()
                continue

            rec_texts = ocr_result.get("rec_texts", [])
            dt_polys = ocr_result.get("dt_polys", [])

            if not rec_texts:
                continue

            # Build (text, bbox) lines sorted by vertical position
            lines: list[dict] = []
            for i, text in enumerate(rec_texts):
                if not text.strip():
                    continue
                poly = dt_polys[i] if i < len(dt_polys) else None
                if poly is not None:
                    pts = np.array(poly)
                    top = float(pts[:, 1].min())
                    bottom = float(pts[:, 1].max())
                    left = float(pts[:, 0].min())
                    right = float(pts[:, 0].max())
                else:
                    top = bottom = left = right = 0.0
                lines.append({"text": text.strip(), "top": top, "bottom": bottom, "left": left, "right": right})

            # Sort by vertical position
            lines.sort(key=lambda x: x["top"])

            # Group into paragraphs by vertical proximity
            paragraphs = _group_into_paragraphs(lines, gap_threshold=20 * zoom)

            del ocr_result  # Release OCR result memory

            for para in paragraphs:
                content = para["text"].strip()
                if not content:
                    continue
                elements.append({
                    "type": "paragraph",
                    "content": content,
                    "page_number": page_idx + 1,
                    "bbox": para.get("bbox"),
                    "heading_level": None,
                })

            # Periodic garbage collection to keep memory in check for large PDFs
            if (page_idx + 1) % 20 == 0:
                gc.collect()
    finally:
        executor.shutdown(wait=False)

    doc.close()
    logger.info("OCR complete: %s — %d elements extracted (%d pages skipped)", file_path.name, len(elements), skipped_pages)
    return elements


def _group_into_paragraphs(
    lines: list[dict], gap_threshold: float = 30
) -> list[dict]:
    """
    Group OCR text lines into paragraphs based on vertical proximity.

    Lines with vertical gap smaller than gap_threshold are merged into one paragraph.
    """
    if not lines:
        return []

    paragraphs: list[dict] = []
    current_texts: list[str] = []
    current_bbox: list[float] | None = None
    prev_bottom = 0.0

    for line in lines:
        top = line["top"]
        bottom = line["bottom"]
        left = line["left"]
        right = line["right"]

        if current_texts and (top - prev_bottom) > gap_threshold:
            # New paragraph
            paragraphs.append({"text": "".join(current_texts), "bbox": current_bbox})
            current_texts = []
            current_bbox = None

        current_texts.append(line["text"])
        if current_bbox is None:
            current_bbox = [left, top, right, bottom]
        else:
            current_bbox[0] = min(current_bbox[0], left)
            current_bbox[1] = min(current_bbox[1], top)
            current_bbox[2] = max(current_bbox[2], right)
            current_bbox[3] = max(current_bbox[3], bottom)
        prev_bottom = bottom

    if current_texts:
        paragraphs.append({"text": "".join(current_texts), "bbox": current_bbox})

    return paragraphs


async def ocr_extract_structured_async(
    file_path: str | Path,
    dpi: int | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[dict]:
    """Async wrapper: runs OCR extraction in a thread pool."""
    return await asyncio.to_thread(ocr_extract_structured, file_path, dpi, progress_callback)
