"""Corpus (user knowledge base) management service."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from backend.db.sqlite import get_connection
from backend.models.corpus import Corpus, CorpusFileType
from backend.services.indexer import index_corpus, remove_index
from backend.services.extract_cache import load_cached, save_cache
from backend.services.ocr_extractor import is_scanned_pdf, ocr_extract_structured
from backend.services.pdf_extractor import compute_file_hash, pymupdf_extract_structured
from backend.services.structured_extractor import extract_structured


async def import_corpus_file(
    file_path: str | Path,
    title: str = "",
    description: str | None = None,
    tags: list[str] | None = None,
) -> Corpus | None:
    """Import a file into the corpus."""
    file_path = Path(file_path)
    if not file_path.exists():
        return None

    suffix = file_path.suffix.lower().lstrip(".")
    file_type_map = {"md": "md", "txt": "txt", "pdf": "pdf", "markdown": "md", "text": "txt"}
    file_type = file_type_map.get(suffix, "txt")

    file_hash = compute_file_hash(file_path)

    # Check for duplicate
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM corpus WHERE file_hash = ?", (file_hash,)
    ).fetchone()
    if existing:
        return None

    # Extract content
    structured_elements: list[dict] | None = None
    if file_type == "pdf":
        cached = load_cached(file_hash)
        if cached is not None:
            structured_elements = cached
        elif is_scanned_pdf(file_path):
            structured_elements = ocr_extract_structured(file_path)
            save_cache(file_hash, structured_elements)
        else:
            quick_elements = pymupdf_extract_structured(file_path)
            structured_elements = extract_structured(file_path, quick_elements=quick_elements)
            save_cache(file_hash, structured_elements)
        content = "\n\n".join(el["content"] for el in structured_elements)
    else:
        content = file_path.read_text(encoding="utf-8", errors="ignore")

    now = datetime.now()
    corpus = Corpus(
        id=str(uuid.uuid4()),
        title=title or file_path.stem,
        description=description,
        file_path=str(file_path),
        file_type=CorpusFileType(file_type),
        file_hash=file_hash,
        tags=tags or [],
        created_at=now,
        updated_at=now,
    )

    # Save to database
    conn.execute(
        """INSERT INTO corpus (id, title, description, file_path, file_type, file_hash, tags, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            corpus.id,
            corpus.title,
            corpus.description,
            corpus.file_path,
            corpus.file_type.value,
            corpus.file_hash,
            json.dumps(corpus.tags),
            corpus.created_at.isoformat(),
            corpus.updated_at.isoformat(),
        ),
    )
    conn.commit()

    # Index with structured elements (for PDFs) or plain text (for MD/TXT)
    await index_corpus(corpus.id, corpus.title, content, structured_elements=structured_elements)

    return corpus
