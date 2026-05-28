"""Lightweight PDF utilities using PyMuPDF.

Handles only quick operations that don't need full structured extraction:
- File hash computation (SHA-256)
- First-pages text extraction for DOI/PMID regex scanning
- PDF embedded metadata reading (doc.metadata)
- DOI / PMID regex matching
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import fitz  # PyMuPDF

# DOI regex: 10.xxxx/...
DOI_PATTERN = re.compile(r'\b(10\.\d{4,9}/[^\s,;}\]\"]+)', re.IGNORECASE)
# PMID regex
PMID_PATTERN = re.compile(r'\bPMID:\s*(\d{6,9})\b', re.IGNORECASE)


def compute_file_hash(file_path: str | Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_first_pages_text(file_path: str | Path, max_pages: int = 2) -> str:
    """Extract text from the first N pages of a PDF (fast, for DOI/PMID scanning)."""
    doc = fitz.open(str(file_path))
    texts = []
    for i in range(min(max_pages, len(doc))):
        texts.append(doc[i].get_text())
    doc.close()
    return "\n".join(texts)


def _decode_pdf_string(value: str) -> str:
    """Decode PDF metadata strings that may be hex-encoded GBK/GB2312."""
    if not value:
        return value
    # Detect hex-wrapped strings like <hex_chars> or raw hex that decodes to GBK
    stripped = value.strip()
    if stripped.startswith("<") and stripped.endswith(">"):
        stripped = stripped[1:-1]
    # Check if it looks like a hex string (even-length, all hex chars)
    if len(stripped) >= 4 and len(stripped) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in stripped):
        try:
            raw = bytes.fromhex(stripped)
            # Try GBK first (superset of GB2312), then latin-1
            for encoding in ("gbk", "gb2312", "utf-8", "latin-1"):
                try:
                    decoded = raw.decode(encoding)
                    # Strip trailing .pdf filename suffix if present
                    if decoded.lower().endswith(".pdf"):
                        decoded = decoded[:-4]
                    # Remove leading number prefix like "377."
                    decoded = re.sub(r"^\d+\.\s*", "", decoded)
                    if decoded:
                        return decoded
                except (UnicodeDecodeError, ValueError):
                    continue
        except ValueError:
            pass
    return value


def extract_pdf_metadata(file_path: str | Path) -> dict:
    """Extract embedded metadata from PDF properties."""
    doc = fitz.open(str(file_path))
    meta = doc.metadata or {}
    doc.close()
    return {
        "title": _decode_pdf_string(meta.get("title", "")),
        "author": _decode_pdf_string(meta.get("author", "")),
        "subject": meta.get("subject", ""),
        "creator": meta.get("creator", ""),
        "producer": meta.get("producer", ""),
        "keywords": meta.get("keywords", ""),
    }


def pymupdf_extract_structured(file_path: str | Path) -> list[dict]:
    """Extract structured elements from a PDF using PyMuPDF.

    Simpler than ODL but much more robust — handles any valid PDF.
    Produces paragraph-level elements with page numbers. Uses font size
    heuristics to detect headings.
    """
    import logging
    logger = logging.getLogger(__name__)

    file_path = Path(file_path)
    doc = fitz.open(str(file_path))
    elements: list[dict] = []

    total_pages = len(doc)
    for page_idx in range(total_pages):
        page = doc[page_idx]
        page_num = page_idx + 1

        # Extract text blocks: (x0, y0, x1, y1, text, block_no, block_type)
        # block_type 0 = text, 1 = image
        blocks = page.get_text("blocks")

        for block in blocks:
            if block[6] != 0:  # skip image blocks
                continue

            text = block[4].strip()
            if not text:
                continue

            # Heuristic heading detection
            el_type = "paragraph"
            heading_level = None

            lines = text.split("\n")
            stripped_first = lines[0].strip() if lines else ""
            if (
                len(lines) <= 2
                and len(stripped_first) < 120
                and stripped_first
                and not stripped_first.endswith((".", ",", ";", ":", "。", "，"))
            ):
                # Numbered section pattern → heading
                m = re.match(r"^(\d+(?:\.\d+)*)\s+\S", stripped_first)
                if m:
                    dots = m.group(1).count(".")
                    el_type = "heading"
                    heading_level = min(dots + 1, 4)
                # ALL CAPS short text → heading
                elif stripped_first.isupper() and len(stripped_first) < 80:
                    el_type = "heading"
                    heading_level = 1

            elements.append({
                "type": el_type,
                "content": text,
                "page_number": page_num,
                "bbox": list(block[:4]),
                "heading_level": heading_level,
            })

        if page_num % 50 == 0:
            logger.info("PyMuPDF extraction: page %d/%d", page_num, total_pages)

    doc.close()
    logger.info("PyMuPDF extraction complete: %d elements from %d pages", len(elements), total_pages)
    return elements


def find_doi(text: str) -> str | None:
    """Find DOI in text."""
    m = DOI_PATTERN.search(text)
    if m:
        return m.group(1).rstrip(".")
    return None


def find_pmid(text: str) -> str | None:
    """Find PMID in text."""
    m = PMID_PATTERN.search(text)
    if m:
        return m.group(1)
    return None
