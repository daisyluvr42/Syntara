"""SQLite database with FTS5 full-text search."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import jieba

from backend.config import SQLITE_DB_PATH

_connection: sqlite3.Connection | None = None


def _jieba_tokenize(text: str) -> str:
    """Tokenize text with jieba for FTS5 indexing."""
    words = jieba.cut_for_search(text)
    tokens: list[str] = []
    for word in words:
        cleaned_parts = re.findall(r"\w+", word, flags=re.UNICODE)
        tokens.extend(part for part in cleaned_parts if part)
    return " ".join(tokens)


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(str(SQLITE_DB_PATH), check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA foreign_keys=ON")
    return _connection


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _get_table_columns(table: str) -> set[str]:
    conn = get_connection()
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def _ensure_column(table: str, definition: str) -> None:
    conn = get_connection()
    column_name = definition.split()[0]
    if column_name not in _get_table_columns(table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")
        conn.commit()


def _sync_literature_processing_state() -> None:
    conn = get_connection()
    columns = _get_table_columns("literature")
    required = {"processing_status", "processing_error", "search_ready_fts", "search_ready_vector"}
    if not required.issubset(columns):
        return

    # Build set of literature IDs that have FTS entries (single query)
    fts_ids: set[str] = {
        r["literature_id"]
        for r in conn.execute("SELECT DISTINCT literature_id FROM literature_fts").fetchall()
    }

    # Build set of literature IDs that have vector entries (single batch query)
    vector_ids: set[str] = set()
    try:
        from backend.db.chromadb_store import get_collection

        collection = get_collection()
        # Fetch all metadatas in one call to extract unique source_ids
        all_data = collection.get(include=["metadatas"])
        for meta in (all_data.get("metadatas") or []):
            sid = (meta or {}).get("source_id")
            if sid:
                vector_ids.add(sid)
    except Exception:
        pass

    rows = conn.execute(
        """
        SELECT id, file_path, full_text, processing_status, processing_error
        FROM literature
        """
    ).fetchall()

    for row in rows:
        lit_id = row["id"]
        full_text = row["full_text"] or ""
        has_full_text = bool(full_text.strip())
        fts_ready = lit_id in fts_ids
        vector_ready = lit_id in vector_ids

        if row["processing_error"]:
            status = "failed"
        elif has_full_text and fts_ready and vector_ready:
            status = "ready"
        elif has_full_text or fts_ready:
            status = "partial"
        elif row["file_path"]:
            status = "processing"
        else:
            status = "partial"

        conn.execute(
            """
            UPDATE literature
            SET processing_status = ?, search_ready_fts = ?, search_ready_vector = ?
            WHERE id = ?
            """,
            (status, int(fts_ready), int(vector_ready), lit_id),
        )

    conn.commit()


def init_db():
    """Create all tables and FTS5 indexes."""
    conn = get_connection()

    # Migration: drop contentless FTS5 tables (content='') and recreate as regular FTS5
    # Contentless tables can't return column values or handle DELETE properly
    for tbl in ("literature_fts", "corpus_fts"):
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tbl,)
        ).fetchone()
        if row and "content=''" in (row[0] or ""):
            conn.execute(f"DROP TABLE {tbl}")
            conn.commit()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS literature (
            id TEXT PRIMARY KEY,
            cite_key TEXT UNIQUE,
            title TEXT NOT NULL DEFAULT '',
            authors TEXT NOT NULL DEFAULT '[]',
            abstract TEXT,
            journal TEXT,
            publisher TEXT,
            volume TEXT,
            issue TEXT,
            pages TEXT,
            year INTEGER,
            date TEXT,
            doi TEXT,
            pmid TEXT,
            pmcid TEXT,
            issn TEXT,
            isbn TEXT,
            type TEXT NOT NULL DEFAULT 'journal_article',
            keywords TEXT NOT NULL DEFAULT '[]',
            tags TEXT NOT NULL DEFAULT '[]',
            language TEXT NOT NULL DEFAULT 'en',
            file_path TEXT,
            file_hash TEXT,
            file_size INTEGER,
            full_text TEXT,
            processing_status TEXT NOT NULL DEFAULT 'ready',
            processing_error TEXT,
            processing_progress TEXT,
            search_ready_fts INTEGER NOT NULL DEFAULT 0,
            search_ready_vector INTEGER NOT NULL DEFAULT 0,
            metadata_sources TEXT NOT NULL DEFAULT '{}',
            metadata_confidence REAL NOT NULL DEFAULT 0.0,
            manually_verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            imported_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS corpus (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            file_path TEXT NOT NULL,
            file_type TEXT NOT NULL DEFAULT 'md',
            file_hash TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS style_profile (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            project TEXT NOT NULL DEFAULT 'default',
            profile_json TEXT NOT NULL DEFAULT '{}',
            profile_markdown TEXT NOT NULL DEFAULT '',
            source_corpus_ids TEXT NOT NULL DEFAULT '[]',
            tags TEXT NOT NULL DEFAULT '[]',
            is_default INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS document (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT 'Untitled',
            content TEXT NOT NULL DEFAULT '',
            csl_style TEXT NOT NULL DEFAULT 'vancouver',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS citation (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            literature_id TEXT NOT NULL,
            cite_key TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            context TEXT NOT NULL DEFAULT '',
            "order" INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE CASCADE,
            FOREIGN KEY (literature_id) REFERENCES literature(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ai_provider_config (
            id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            name TEXT NOT NULL,
            api_base TEXT NOT NULL,
            api_key TEXT,
            model_id TEXT NOT NULL,
            is_default INTEGER NOT NULL DEFAULT 0,
            max_tokens INTEGER NOT NULL DEFAULT 4096,
            temperature REAL NOT NULL DEFAULT 0.7
        );

        -- Search query history
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lang TEXT NOT NULL,
            query TEXT NOT NULL,
            used_at TEXT NOT NULL,
            UNIQUE(lang, query)
        );

        -- Dismissed search hits (per query key)
        CREATE TABLE IF NOT EXISTS dismissed_hits (
            query_key TEXT NOT NULL,
            lit_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            dismissed_at TEXT NOT NULL,
            PRIMARY KEY (query_key, lit_id, chunk_index)
        );

        -- FTS5 virtual table for full-text search
        CREATE VIRTUAL TABLE IF NOT EXISTS literature_fts USING fts5(
            literature_id,
            title,
            abstract,
            full_text,
            tokenize='unicode61'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS corpus_fts USING fts5(
            corpus_id,
            title,
            content,
            tokenize='unicode61'
        );
    """)
    _ensure_column("literature", "processing_status TEXT NOT NULL DEFAULT 'ready'")
    _ensure_column("literature", "processing_error TEXT")
    _ensure_column("literature", "processing_progress TEXT")
    _ensure_column("literature", "search_ready_fts INTEGER NOT NULL DEFAULT 0")
    _ensure_column("literature", "search_ready_vector INTEGER NOT NULL DEFAULT 0")
    _sync_literature_processing_state()
    conn.commit()


def index_literature_fts(lit_id: str, title: str, abstract: str | None, full_text: str | None):
    """Index a literature entry in FTS5 with jieba tokenization."""
    conn = get_connection()
    # Tokenize for better CJK search
    title_tok = _jieba_tokenize(title) if title else ""
    abstract_tok = _jieba_tokenize(abstract) if abstract else ""
    full_text_tok = _jieba_tokenize(full_text) if full_text else ""

    # Remove old entry
    conn.execute("DELETE FROM literature_fts WHERE literature_id = ?", (lit_id,))
    conn.execute(
        "INSERT INTO literature_fts (literature_id, title, abstract, full_text) VALUES (?, ?, ?, ?)",
        (lit_id, title_tok, abstract_tok, full_text_tok),
    )
    conn.commit()


def search_literature_fts(query: str, limit: int = 20) -> list[dict]:
    """Search literature using FTS5."""
    conn = get_connection()
    tokenized = _jieba_tokenize(query)
    if not tokenized:
        return []
    rows = conn.execute(
        """
        SELECT literature_id, rank
        FROM literature_fts
        WHERE literature_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (tokenized, limit),
    ).fetchall()
    return [{"id": r["literature_id"], "score": -r["rank"]} for r in rows]


def index_corpus_fts(corpus_id: str, title: str, content: str):
    """Index a corpus entry in FTS5."""
    conn = get_connection()
    title_tok = _jieba_tokenize(title)
    content_tok = _jieba_tokenize(content)
    conn.execute("DELETE FROM corpus_fts WHERE corpus_id = ?", (corpus_id,))
    conn.execute(
        "INSERT INTO corpus_fts (corpus_id, title, content) VALUES (?, ?, ?)",
        (corpus_id, title_tok, content_tok),
    )
    conn.commit()


def search_corpus_fts(query: str, limit: int = 20) -> list[dict]:
    """Search corpus using FTS5."""
    conn = get_connection()
    tokenized = _jieba_tokenize(query)
    if not tokenized:
        return []
    rows = conn.execute(
        """
        SELECT corpus_id, rank
        FROM corpus_fts
        WHERE corpus_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (tokenized, limit),
    ).fetchall()
    return [{"id": r["corpus_id"], "score": -r["rank"]} for r in rows]
