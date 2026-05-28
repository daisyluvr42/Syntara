"""PubMed search and import API router."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.db.sqlite import get_connection
from backend.services.indexer import index_literature
from backend.services.metadata import generate_cite_key
from backend.services.pubmed import (
    FIELD_TAGS,
    SORT_OPTIONS,
    build_query,
    fetch_pubmed_metadata,
    get_pmc_pdf_url,
    search_pubmed,
)

router = APIRouter(prefix="/api/pubmed", tags=["pubmed"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class SearchTerm(BaseModel):
    term: str
    field: str = "All Fields"
    op: str = "AND"  # AND / OR / NOT


class AdvancedSearchRequest(BaseModel):
    """Supports both structured builder and raw query modes."""
    terms: list[SearchTerm] | None = None
    raw_query: str | None = None
    max_results: int = 20
    page: int = 1
    sort: str = "relevance"
    date_type: str | None = None
    min_date: str | None = None
    max_date: str | None = None
    rel_date: int | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/fields")
async def get_fields():
    """Return available search fields and sort options for the UI."""
    return {
        "fields": list(FIELD_TAGS.keys()),
        "sort_options": SORT_OPTIONS,
    }


@router.get("/search")
async def pubmed_search_simple(query: str, max_results: int = 20):
    """Simple keyword search (backward compatible)."""
    result = await search_pubmed(query, max_results)
    pmids = result["pmids"]
    if not pmids:
        return {"results": [], "total": result["count"], "query_translation": result["query_translation"]}

    metadata_list = await fetch_pubmed_metadata(pmids)
    return {
        "results": metadata_list,
        "total": result["count"],
        "query_translation": result["query_translation"],
    }


@router.post("/search/advanced")
async def pubmed_search_advanced(req: AdvancedSearchRequest):
    """Advanced search with structured terms, date filters, sort, pagination."""
    query = build_query(
        terms=[t.model_dump() for t in req.terms] if req.terms else None,
        raw_query=req.raw_query,
    )
    if not query:
        raise HTTPException(400, "No search terms provided")

    result = await search_pubmed(
        query=query,
        max_results=req.max_results,
        sort=req.sort,
        page=req.page,
        date_type=req.date_type,
        min_date=req.min_date,
        max_date=req.max_date,
        rel_date=req.rel_date,
    )
    pmids = result["pmids"]
    metadata_list = await fetch_pubmed_metadata(pmids) if pmids else []

    return {
        "results": metadata_list,
        "total": result["count"],
        "page": req.page,
        "max_results": req.max_results,
        "pages": (result["count"] + req.max_results - 1) // req.max_results if req.max_results else 1,
        "built_query": query,
        "query_translation": result["query_translation"],
    }


@router.post("/import")
async def import_from_pubmed(pmids: list[str]):
    """Import selected PubMed articles into the literature library."""
    if not pmids:
        raise HTTPException(400, "No PMIDs provided")

    metadata_list = await fetch_pubmed_metadata(pmids)
    conn = get_connection()

    existing_keys = {
        r["cite_key"] for r in conn.execute("SELECT cite_key FROM literature").fetchall()
    }
    existing_pmids = {
        r["pmid"]
        for r in conn.execute("SELECT pmid FROM literature WHERE pmid IS NOT NULL").fetchall()
    }

    imported = []
    skipped = []

    for meta in metadata_list:
        pmid = meta.get("pmid", "")
        if pmid in existing_pmids:
            skipped.append({"pmid": pmid, "reason": "already exists"})
            continue

        authors = meta.get("authors", [])
        year = meta.get("year")
        cite_key = generate_cite_key(authors, year, existing_keys, title=meta.get("title", ""))
        existing_keys.add(cite_key)

        lit_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        conn.execute(
            """INSERT INTO literature (id, cite_key, title, authors, abstract, journal, publisher,
               volume, issue, pages, year, date, doi, pmid, pmcid, issn, isbn,
               type, keywords, tags, language, metadata_sources, metadata_confidence,
               manually_verified, processing_status, processing_error, search_ready_fts,
               search_ready_vector, created_at, updated_at, imported_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                lit_id, cite_key, meta.get("title", ""),
                json.dumps(authors),
                meta.get("abstract", ""), meta.get("journal", ""), None,
                meta.get("volume"), meta.get("issue"), meta.get("pages"),
                year, None, meta.get("doi"), pmid, meta.get("pmcid"),
                None, None,
                "journal_article", json.dumps(meta.get("keywords", [])), json.dumps([]),
                meta.get("language", "en") or "en",
                json.dumps({"all": "pubmed"}), 0.8, 0,
                "partial", None, 0, 0,
                now, now, now,
            ),
        )
        conn.commit()

        # Index (no full text yet, just metadata)
        await index_literature(lit_id, meta.get("title", ""), meta.get("abstract", ""), None)
        conn.execute(
            """
            UPDATE literature
            SET search_ready_fts = 1, search_ready_vector = 0, processing_status = 'partial'
            WHERE id = ?
            """,
            (lit_id,),
        )
        conn.commit()

        imported.append({
            "id": lit_id,
            "cite_key": cite_key,
            "title": meta.get("title", ""),
            "pmid": pmid,
        })

    return {"imported": imported, "skipped": skipped}


@router.get("/pdf-url/{pmcid}")
async def get_pdf_url(pmcid: str):
    """Get PDF download URL for a PMC article."""
    url = await get_pmc_pdf_url(pmcid)
    if not url:
        raise HTTPException(404, "PDF not available for this article")
    return {"url": url}
