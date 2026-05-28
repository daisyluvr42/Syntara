"""Indexing service: FTS5 + vector embeddings with structure-aware chunking."""

from __future__ import annotations

import uuid

from backend.db import chromadb_store, sqlite
from backend.models.chunk import SourceType
from backend.services.embedder import EmbeddingServiceUnavailable, get_embeddings
from backend.services.odl_extractor import build_structured_chunks


async def index_literature(
    lit_id: str,
    title: str,
    abstract: str | None,
    full_text: str | None,
    structured_elements: list[dict] | None = None,
) -> int:
    """Index a literature entry in both FTS5 and ChromaDB."""
    # FTS5 keyword indexing (uses flat text)
    sqlite.index_literature_fts(lit_id, title, abstract, full_text)

    # Vector indexing (uses structured elements for smart chunking)
    if structured_elements:
        chunks = build_structured_chunks(structured_elements)
        try:
            return await _store_chunks(lit_id, SourceType.literature, chunks, title)
        except EmbeddingServiceUnavailable:
            return 0
    return 0


async def index_corpus(
    corpus_id: str,
    title: str,
    content: str,
    structured_elements: list[dict] | None = None,
) -> int:
    """Index a corpus entry in both FTS5 and ChromaDB."""
    sqlite.index_corpus_fts(corpus_id, title, content)

    if structured_elements:
        chunks = build_structured_chunks(structured_elements)
    else:
        # Non-PDF corpus (MD/TXT): wrap as simple paragraph elements
        chunks = _text_to_simple_chunks(content)

    try:
        return await _store_chunks(corpus_id, SourceType.corpus, chunks, title)
    except EmbeddingServiceUnavailable:
        return 0


async def remove_index(source_id: str):
    """Remove all index entries for a source."""
    chromadb_store.delete_by_source(source_id)


async def _store_chunks(
    source_id: str,
    source_type: SourceType,
    chunks: list[dict],
    title: str,
) -> int:
    """Embed chunks and store in ChromaDB."""
    if not chunks:
        return 0

    # Remove old chunks
    chromadb_store.delete_by_source(source_id)

    # Generate embeddings in batches
    batch_size = 32
    stored = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["content"] for c in batch]

        embeddings = await get_embeddings(texts)

        ids = [str(uuid.uuid4()) for _ in batch]
        metadatas = [
            {
                "source_id": source_id,
                "source_type": source_type.value,
                "chunk_index": c["chunk_index"],
                "title": title,
                "element_type": c.get("element_type", "paragraph"),
                "heading": c.get("heading", ""),
                "page_number": c.get("page_number", 0),
            }
            for c in batch
        ]

        chromadb_store.add_chunks(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        stored += len(ids)

    return stored


def _text_to_simple_chunks(text: str, chunk_size: int = 500) -> list[dict]:
    """Split plain text (MD/TXT) into simple paragraph chunks."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks = []
    buffer = ""
    idx = 0

    for para in paragraphs:
        if len(buffer) + len(para) > chunk_size and buffer:
            chunks.append({
                "content": buffer.strip(),
                "chunk_index": idx,
                "element_type": "paragraph",
                "heading": "",
                "page_number": 0,
            })
            idx += 1
            buffer = para
        else:
            buffer = (buffer + "\n" + para).strip() if buffer else para

    if buffer.strip():
        chunks.append({
            "content": buffer.strip(),
            "chunk_index": idx,
            "element_type": "paragraph",
            "heading": "",
            "page_number": 0,
        })

    return chunks
