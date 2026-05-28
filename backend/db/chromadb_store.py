"""ChromaDB vector store for semantic search."""

from __future__ import annotations

import chromadb
from chromadb.config import Settings

from backend.config import CHROMADB_DIR

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None

COLLECTION_NAME = "syntara_chunks"


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(CHROMADB_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = get_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_chunks(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
):
    """Add chunks with embeddings to the vector store."""
    collection = get_collection()
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def search_chunks(
    query_embedding: list[float],
    n_results: int = 10,
    where: dict | None = None,
) -> dict:
    """Search for similar chunks."""
    collection = get_collection()
    kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    return collection.query(**kwargs)


def delete_by_source(source_id: str):
    """Delete all chunks belonging to a source."""
    collection = get_collection()
    collection.delete(where={"source_id": source_id})


def get_collection_count() -> int:
    return get_collection().count()
