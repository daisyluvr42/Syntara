"""Metadata extraction and merging service.

Split into two phases:
  - Phase A (fast, <3s): hash, dedup, DOI/PMID scan, API metadata, PDF metadata, cite key
  - Phase B (background): Full structured extraction (ODL/PyMuPDF/OCR) → cache → index → tree
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from backend.models.literature import Author, Literature
from backend.services.crossref import fetch_metadata_by_doi
from backend.services.ocr_extractor import is_scanned_pdf
from backend.services.pdf_extractor import (
    compute_file_hash,
    extract_first_pages_text,
    extract_pdf_metadata,
    find_doi,
    find_pmid,
)
from backend.services.pubmed import fetch_pubmed_metadata


@dataclass
class ImportResult:
    """Result of Phase A (fast metadata extraction)."""
    literature: Literature
    is_scanned: bool = False


_STOP_WORDS = {
    "a", "an", "the", "of", "in", "on", "for", "and", "to", "with", "from",
    "by", "at", "is", "are", "was", "were", "new", "its",
}


def _title_to_name(title: str) -> str:
    """Extract a short, meaningful slug from a title for use in cite keys.

    For mixed Chinese/English titles, prefers English words.
    For pure Chinese titles, uses pinyin transliteration.
    Returns lowercase ASCII string, or empty string if nothing useful found.
    """
    # Extract ASCII words from the title (works for English and mixed titles)
    words = re.findall(r"[a-zA-Z]{2,}", title)
    # Filter stop words and take first 2 significant words
    significant = [w.lower() for w in words if w.lower() not in _STOP_WORDS]
    if significant:
        return "".join(significant[:2])

    # Fallback: Chinese title → pinyin (first 2-3 meaningful characters)
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", title)
    if chinese_chars:
        try:
            from pypinyin import lazy_pinyin
            # Take first 3 Chinese characters and convert to pinyin
            slug = "".join(lazy_pinyin(chinese_chars[:3]))
            slug = re.sub(r"[^a-z]", "", slug)
            if slug:
                return slug
        except ImportError:
            pass
    return ""


def generate_cite_key(
    authors: list[dict],
    year: int | None,
    existing_keys: set[str],
    title: str = "",
) -> str:
    """Generate citation key from title (primary) + year.

    Title is the primary source since it's almost always extractable.
    Author family name is used only as a fallback when title yields nothing.
    """
    name = _title_to_name(title) if title else ""

    if not name:
        # Fallback to author family name
        if authors and authors[0].get("family"):
            name = authors[0]["family"].lower().strip()
            name = re.sub(r"[^a-z0-9]", "", name)
        else:
            name = "unknown"

    base = f"{name}{year or 'nd'}"
    key = base
    suffix_idx = 0
    while key in existing_keys:
        suffix_idx += 1
        key = f"{base}{chr(96 + suffix_idx)}"  # a, b, c, ...
    return key


async def process_pdf_metadata(
    file_path: str | Path,
    existing_keys: set[str],
    existing_hashes: set[str],
) -> ImportResult | None:
    """Phase A: Fast metadata extraction only (no heavy PDF parsing).

    Takes <3 seconds for any PDF. Returns the Literature record immediately.
    Full-text extraction and indexing happen in Phase B (background).
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return None

    # Step 1: File hash for dedup
    file_hash = compute_file_hash(file_path)
    if file_hash in existing_hashes:
        return None  # Duplicate

    # Step 2: Extract first pages text (fast PyMuPDF scan for DOI/PMID)
    first_pages = extract_first_pages_text(file_path)

    # Step 3: Find DOI or PMID
    doi = find_doi(first_pages)
    pmid = find_pmid(first_pages)

    metadata: dict = {}
    sources: dict[str, str] = {}

    # Step 4: Try API metadata retrieval
    if doi:
        crossref_meta = await fetch_metadata_by_doi(doi)
        if crossref_meta:
            metadata = crossref_meta
            for k in crossref_meta:
                if crossref_meta[k]:
                    sources[k] = "crossref"

    if pmid and not metadata.get("title"):
        pubmed_results = await fetch_pubmed_metadata([pmid])
        if pubmed_results:
            pm = pubmed_results[0]
            for k, v in pm.items():
                if v and not metadata.get(k):
                    metadata[k] = v
                    sources[k] = "pubmed"

    # Step 5: Fallback to PDF embedded metadata
    if not metadata.get("title"):
        pdf_meta = extract_pdf_metadata(file_path)
        if pdf_meta.get("title"):
            metadata["title"] = pdf_meta["title"]
            sources["title"] = "pdf_meta"
        if pdf_meta.get("author") and not metadata.get("authors"):
            names = pdf_meta["author"].split(";")
            metadata["authors"] = [
                {"family": n.strip().split()[-1] if n.strip() else "",
                 "given": " ".join(n.strip().split()[:-1]) if len(n.strip().split()) > 1 else ""}
                for n in names if n.strip()
            ]
            sources["authors"] = "pdf_meta"

    # Step 6: Generate cite key
    authors_list = metadata.get("authors", [])
    year = metadata.get("year")
    title = metadata.get("title", file_path.stem)
    cite_key = generate_cite_key(authors_list, year, existing_keys, title=title)

    # Step 7: Quick scanned PDF detection (checks first few pages, fast)
    scanned = is_scanned_pdf(file_path)
    sources["full_text"] = "pending"  # Will be filled by Phase B

    # Build Literature object (no full_text yet — filled by background task)
    now = datetime.now()
    lit = Literature(
        id=str(uuid.uuid4()),
        cite_key=cite_key,
        title=metadata.get("title", file_path.stem),
        authors=[Author(**a) for a in authors_list],
        abstract=metadata.get("abstract"),
        journal=metadata.get("journal"),
        publisher=metadata.get("publisher"),
        volume=metadata.get("volume"),
        issue=metadata.get("issue"),
        pages=metadata.get("pages"),
        year=year,
        date=metadata.get("date"),
        doi=doi or metadata.get("doi"),
        pmid=pmid or metadata.get("pmid"),
        pmcid=metadata.get("pmcid"),
        issn=metadata.get("issn"),
        isbn=metadata.get("isbn"),
        type=metadata.get("type", "journal_article"),
        keywords=metadata.get("keywords", []),
        language="en",  # Will be updated by Phase B after full text is available
        file_path=str(file_path),
        file_hash=file_hash,
        file_size=file_path.stat().st_size,
        full_text="",  # Filled by Phase B
        metadata_sources=sources,
        metadata_confidence=_calc_confidence(sources, metadata),
        created_at=now,
        updated_at=now,
        imported_at=now,
    )
    return ImportResult(literature=lit, is_scanned=scanned)


def _detect_language(text: str) -> str:
    """Simple heuristic for Chinese vs English."""
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    if chinese_chars > len(text) * 0.1:
        return "zh"
    return "en"


def _calc_confidence(sources: dict, metadata: dict) -> float:
    """Calculate metadata confidence score."""
    key_fields = ["title", "authors", "year", "doi", "journal"]
    filled = sum(1 for k in key_fields if metadata.get(k))
    api_sourced = sum(1 for k in key_fields if sources.get(k) in ("crossref", "pubmed"))
    base = filled / len(key_fields)
    bonus = api_sourced / len(key_fields) * 0.3
    return min(1.0, base + bonus)
