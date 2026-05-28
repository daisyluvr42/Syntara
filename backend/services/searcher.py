"""Search services for literature and corpus retrieval."""

from __future__ import annotations

import json
import re
from collections import defaultdict

from backend.db import chromadb_store, sqlite
from backend.services.ai_provider import chat_completion
from backend.services.embedder import EmbeddingServiceUnavailable, get_single_embedding
from backend.services.extract_cache import load_cached
from backend.services.odl_extractor import build_structured_chunks


async def hybrid_search(
    query: str,
    scope: str = "all",  # all, literature, corpus
    top_k: int = 20,
    project: str | None = None,
) -> list[dict]:
    """
    Perform hybrid search combining FTS5 keyword search and vector semantic search.
    Results are fused using Reciprocal Rank Fusion (RRF).
    """
    fetch_k = max(top_k * 5, 50) if project else top_k
    fts_results = _fts_search(query, scope, fetch_k)
    try:
        vector_results = await _vector_search(query, scope, fetch_k)
    except EmbeddingServiceUnavailable:
        vector_results = []

    fused = _rrf_fusion(fts_results, vector_results, k=60)
    return _enrich_results(fused, project=project)[:top_k]


async def grouped_literature_search(
    zh_query: str = "",
    en_query: str = "",
    provider_id: str | None = None,
    top_k: int = 20,
    project: str | None = None,
) -> dict:
    """Search literature and group all matching chunks by literature record."""
    zh_query = zh_query.strip()
    en_query = en_query.strip()
    warnings: list[str] = []
    used_queries: list[dict] = []

    if zh_query:
        used_queries.append({"lang": "zh", "text": zh_query, "source": "user"})
    if en_query:
        used_queries.append({"lang": "en", "text": en_query, "source": "user"})

    if zh_query and not en_query:
        translated = await _complete_missing_query(zh_query, "en", provider_id)
        if translated:
            used_queries.append({"lang": "en", "text": translated, "source": "ai"})
        else:
            warnings.append("未能补全英文检索词，当前仅使用中文检索词。")
    elif en_query and not zh_query:
        translated = await _complete_missing_query(en_query, "zh", provider_id)
        if translated:
            used_queries.append({"lang": "zh", "text": translated, "source": "ai"})
        else:
            warnings.append("未能补全中文检索词，当前仅使用英文检索词。")

    queries = _dedupe_queries(used_queries)
    if not queries:
        return {
            "semantic_available": True,
            "warnings": warnings,
            "used_queries": [],
            "results": [],
            "total": 0,
        }

    doc_scores: dict[str, float] = defaultdict(float)
    doc_languages: dict[str, set[str]] = defaultdict(set)
    vector_hits_by_doc: dict[str, dict[int, dict]] = defaultdict(dict)

    candidate_limit = max(top_k * 5, 50)
    vector_limit = max(top_k * 20, 80)
    semantic_available = True

    for query in queries:
        for rank, hit in enumerate(sqlite.search_literature_fts(query["text"], candidate_limit)):
            lit_id = hit["id"]
            doc_scores[lit_id] += 1.0 / (60 + rank + 1)
            doc_languages[lit_id].add(query["lang"])

        if not semantic_available:
            continue

        try:
            vector_hits = await _vector_search(query["text"], "literature", vector_limit)
        except EmbeddingServiceUnavailable:
            semantic_available = False
            warnings.append("语义检索当前不可用，结果已降级为关键词检索。")
            vector_hits = []

        for rank, hit in enumerate(vector_hits):
            lit_id = hit["id"]
            if not lit_id:
                continue

            doc_scores[lit_id] += 1.0 / (60 + rank + 1)
            doc_languages[lit_id].add(query["lang"])

            chunk_index = int(hit.get("chunk_index", rank) or rank)
            entry = vector_hits_by_doc[lit_id].get(chunk_index)
            highlights = _find_highlights(hit.get("snippet", ""), query["terms"])
            if entry is None:
                vector_hits_by_doc[lit_id][chunk_index] = {
                    "chunk_index": chunk_index,
                    "content": hit.get("snippet", ""),
                    "heading": hit.get("heading", ""),
                    "page_number": hit.get("page_number", 0),
                    "element_type": hit.get("element_type", "paragraph"),
                    "score": hit.get("score", 0.0),
                    "matched_by": {f"{query['lang']}:semantic"},
                    "matched_terms": set(_matched_terms(hit.get("snippet", ""), query["terms"])),
                    "highlights": highlights,
                }
            else:
                entry["score"] = max(entry["score"], hit.get("score", 0.0))
                entry["matched_by"].add(f"{query['lang']}:semantic")
                entry["matched_terms"].update(_matched_terms(hit.get("snippet", ""), query["terms"]))
                entry["highlights"] = _merge_highlights(entry["highlights"], highlights)

    if not doc_scores:
        return {
            "semantic_available": semantic_available,
            "warnings": warnings,
            "used_queries": queries,
            "results": [],
            "total": 0,
        }

    conn = sqlite.get_connection()
    sorted_ids = sorted(doc_scores, key=lambda lit_id: doc_scores[lit_id], reverse=True)
    placeholders = ",".join("?" for _ in sorted_ids)
    params = list(sorted_ids)
    project_clause = ""
    if project:
        project_clause = " AND tags LIKE ?"
        params.append(f"%project:{project}%")
    rows = conn.execute(
        f"""
        SELECT id, cite_key, title, authors, year, journal, abstract, file_hash, full_text
        FROM literature
        WHERE id IN ({placeholders}){project_clause}
        """,
        params,
    ).fetchall()
    row_map = {row["id"]: row for row in rows}

    results = []
    for lit_id in sorted_ids:
        row = row_map.get(lit_id)
        if row is None:
            continue

        hits_map = dict(vector_hits_by_doc.get(lit_id, {}))
        for chunk in _load_search_chunks(row):
            for query in queries:
                highlights = _find_highlights(chunk["content"], query["terms"])
                if not highlights:
                    continue

                chunk_index = int(chunk["chunk_index"])
                entry = hits_map.get(chunk_index)
                if entry is None:
                    hits_map[chunk_index] = {
                        "chunk_index": chunk_index,
                        "content": chunk["content"],
                        "heading": chunk.get("heading", ""),
                        "page_number": chunk.get("page_number", 0),
                        "element_type": chunk.get("element_type", "paragraph"),
                        "score": 0.35 + min(0.3, len(highlights) * 0.05),
                        "matched_by": {f"{query['lang']}:fts"},
                        "matched_terms": set(_matched_terms(chunk["content"], query["terms"])),
                        "highlights": highlights,
                    }
                else:
                    entry["score"] = max(entry["score"], 0.35 + min(0.3, len(highlights) * 0.05))
                    entry["matched_by"].add(f"{query['lang']}:fts")
                    entry["matched_terms"].update(_matched_terms(chunk["content"], query["terms"]))
                    entry["highlights"] = _merge_highlights(entry["highlights"], highlights)

        # Ensure semantic-only hits get highlights from all query terms
        all_terms = [t for q in queries for t in q["terms"]]
        for hit in hits_map.values():
            if not hit["highlights"] and hit["content"].strip():
                hit["highlights"] = _find_highlights(hit["content"], all_terms)
                hit["matched_terms"].update(_matched_terms(hit["content"], all_terms))

        # Boost hits that match full query phrases (not just sub-terms)
        full_phrases = [q["terms"][0] for q in queries if q["terms"]]
        for hit in hits_map.values():
            content_lower = hit["content"].casefold()
            exact_count = sum(1 for phrase in full_phrases if phrase.casefold() in content_lower)
            if exact_count:
                hit["score"] += 1.0 + exact_count * 0.5  # strong boost for exact phrase match

        hits = sorted(
            (
                {
                    "chunk_index": hit["chunk_index"],
                    "content": hit["content"],
                    "heading": hit["heading"],
                    "page_number": hit["page_number"],
                    "element_type": hit["element_type"],
                    "score": hit["score"],
                    "matched_by": sorted(hit["matched_by"]),
                    "matched_terms": sorted(hit["matched_terms"]),
                    "highlights": hit["highlights"],
                }
                for hit in hits_map.values()
                if hit["content"].strip()
            ),
            key=lambda hit: (-hit["score"], hit["page_number"], hit["chunk_index"]),
        )

        if not hits:
            continue

        preview_content, preview_highlights = _make_preview(
            hits[0]["content"], hits[0]["highlights"]
        )
        results.append(
            {
                "id": lit_id,
                "cite_key": row["cite_key"],
                "title": row["title"],
                "authors": json.loads(row["authors"]) if row["authors"] else [],
                "year": row["year"],
                "journal": row["journal"],
                "hit_count": len(hits),
                "top_score": doc_scores[lit_id],
                "match_languages": sorted(doc_languages.get(lit_id, set())),
                "preview_hit": {
                    "content": preview_content,
                    "highlights": preview_highlights,
                    "heading": hits[0]["heading"],
                    "page_number": hits[0]["page_number"],
                },
                "hits": hits,
            }
        )

        if len(results) >= top_k:
            break

    return {
        "semantic_available": semantic_available,
        "warnings": warnings,
        "used_queries": queries,
        "results": results,
        "total": len(results),
    }


def _fts_search(query: str, scope: str, limit: int) -> list[dict]:
    """FTS5 keyword search."""
    results = []
    if scope in ("all", "literature"):
        hits = sqlite.search_literature_fts(query, limit)
        for hit in hits:
            results.append(
                {
                    "id": hit["id"],
                    "source_type": "literature",
                    "score": hit["score"],
                }
            )

    if scope in ("all", "corpus"):
        hits = sqlite.search_corpus_fts(query, limit)
        for hit in hits:
            results.append(
                {
                    "id": hit["id"],
                    "source_type": "corpus",
                    "score": hit["score"],
                }
            )

    return results


async def _vector_search(query: str, scope: str, limit: int) -> list[dict]:
    """Vector semantic search via ChromaDB."""
    embedding = await get_single_embedding(query)
    if not embedding:
        return []

    where = None
    if scope == "literature":
        where = {"source_type": "literature"}
    elif scope == "corpus":
        where = {"source_type": "corpus"}

    raw = chromadb_store.search_chunks(embedding, n_results=limit, where=where)

    results = []
    if raw and raw.get("ids") and raw["ids"][0]:
        for i, _chunk_id in enumerate(raw["ids"][0]):
            meta = raw["metadatas"][0][i] if raw.get("metadatas") else {}
            distance = raw["distances"][0][i] if raw.get("distances") else 1.0
            doc_text = raw["documents"][0][i] if raw.get("documents") else ""
            results.append(
                {
                    "id": meta.get("source_id", ""),
                    "source_type": meta.get("source_type", "literature"),
                    "score": 1.0 - distance,
                    "snippet": doc_text,
                    "chunk_index": meta.get("chunk_index", i),
                    "chunk_title": meta.get("title", ""),
                    "element_type": meta.get("element_type", "paragraph"),
                    "heading": meta.get("heading", ""),
                    "page_number": meta.get("page_number", 0),
                }
            )

    return results


def _rrf_fusion(
    fts_results: list[dict],
    vector_results: list[dict],
    k: int = 60,
) -> list[dict]:
    """Reciprocal Rank Fusion of two result lists."""
    scores: dict[str, float] = {}
    snippets: dict[str, str] = {}
    source_types: dict[str, str] = {}
    chunk_meta: dict[str, dict] = {}

    for rank, result in enumerate(fts_results):
        result_id = result["id"]
        scores[result_id] = scores.get(result_id, 0) + 1.0 / (k + rank + 1)
        source_types[result_id] = result.get("source_type", "literature")

    for rank, result in enumerate(vector_results):
        result_id = result["id"]
        scores[result_id] = scores.get(result_id, 0) + 1.0 / (k + rank + 1)
        source_types[result_id] = result.get("source_type", "literature")
        if result.get("snippet"):
            snippets[result_id] = result["snippet"]
        if result_id not in chunk_meta:
            chunk_meta[result_id] = {
                "element_type": result.get("element_type", "paragraph"),
                "heading": result.get("heading", ""),
                "page_number": result.get("page_number", 0),
            }

    sorted_ids = sorted(scores, key=lambda result_id: scores[result_id], reverse=True)
    return [
        {
            "id": result_id,
            "source_type": source_types.get(result_id, "literature"),
            "score": scores[result_id],
            "snippet": snippets.get(result_id, ""),
            "element_type": chunk_meta.get(result_id, {}).get("element_type", "paragraph"),
            "heading": chunk_meta.get(result_id, {}).get("heading", ""),
            "page_number": chunk_meta.get(result_id, {}).get("page_number", 0),
        }
        for result_id in sorted_ids
    ]


def _enrich_results(results: list[dict], project: str | None = None) -> list[dict]:
    """Add metadata from SQLite to search results."""
    conn = sqlite.get_connection()

    enriched = []
    for result in results:
        if result["source_type"] == "literature":
            row = conn.execute(
                "SELECT id, cite_key, title, authors, year, journal, abstract, tags FROM literature WHERE id = ?",
                (result["id"],),
            ).fetchone()
            if row:
                tags = json.loads(row["tags"]) if row["tags"] else []
                if project and f"project:{project}" not in tags:
                    continue
                result["cite_key"] = row["cite_key"]
                result["title"] = row["title"]
                result["authors"] = json.loads(row["authors"]) if row["authors"] else []
                result["year"] = row["year"]
                result["journal"] = row["journal"]
                result["abstract"] = row["abstract"]
                result["tags"] = tags
                enriched.append(result)
        elif result["source_type"] == "corpus":
            row = conn.execute(
                "SELECT id, title, description, tags FROM corpus WHERE id = ?",
                (result["id"],),
            ).fetchone()
            if row:
                tags = json.loads(row["tags"]) if row["tags"] else []
                if project and f"project:{project}" not in tags:
                    continue
                result["title"] = row["title"]
                result["description"] = row["description"]
                result["tags"] = tags
                enriched.append(result)

    return enriched


async def _complete_missing_query(
    query: str,
    target_lang: str,
    provider_id: str | None,
) -> str | None:
    """Use the configured AI provider to fill the missing query language."""
    system_prompt = (
        "You translate academic literature search queries. Preserve technical terminology. "
        "Return only the translated query text, with no explanation or quotes."
    )
    target_name = "English" if target_lang == "en" else "Chinese"

    try:
        result = await chat_completion(
            provider_id,
            [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Translate this search query into {target_name}: {query}",
                },
            ],
            max_tokens=64,
            temperature=0,
        )
    except Exception:
        return None

    cleaned = result.strip().strip('"').strip("'")
    return cleaned or None


def _dedupe_queries(queries: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for query in queries:
        text = query["text"].strip()
        key = (query["lang"], text.casefold())
        if not text or key in seen:
            continue
        deduped.append(
            {
                "lang": query["lang"],
                "text": text,
                "source": query["source"],
                "terms": _extract_terms(text),
            }
        )
        seen.add(key)
    return deduped


def _extract_terms(query: str) -> list[str]:
    terms = [query.strip()]
    terms.extend(token for token in sqlite._jieba_tokenize(query).split() if len(token) > 1)
    terms.extend(
        token
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-_/]+", query)
        if len(token) > 1
    )

    seen: set[str] = set()
    deduped: list[str] = []
    for term in sorted(terms, key=len, reverse=True):
        key = term.casefold()
        if term and key not in seen:
            deduped.append(term)
            seen.add(key)
    return deduped


def _matched_terms(content: str, terms: list[str]) -> list[str]:
    lowered = content.casefold()
    return [term for term in terms if term.casefold() in lowered]


def _find_highlights(content: str, terms: list[str]) -> list[dict]:
    ranges: list[tuple[int, int]] = []
    for term in terms:
        if not term:
            continue
        for match in re.finditer(re.escape(term), content, flags=re.IGNORECASE):
            ranges.append((match.start(), match.end()))

    if not ranges:
        return []

    merged: list[tuple[int, int]] = []
    for start, end in sorted(ranges):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            prev_start, prev_end = merged[-1]
            merged[-1] = (prev_start, max(prev_end, end))

    return [
        {"start": start, "end": end, "text": content[start:end]}
        for start, end in merged
    ]


def _merge_highlights(existing: list[dict], incoming: list[dict]) -> list[dict]:
    if not existing:
        return incoming
    if not incoming:
        return existing
    merged_ranges = [(item["start"], item["end"]) for item in existing + incoming]
    collapsed: list[tuple[int, int]] = []
    for start, end in sorted(merged_ranges):
        if not collapsed or start > collapsed[-1][1]:
            collapsed.append((start, end))
        else:
            prev_start, prev_end = collapsed[-1]
            collapsed[-1] = (prev_start, max(prev_end, end))
    return [
        {"start": start, "end": end}
        for start, end in collapsed
    ]


def _make_preview(content: str, highlights: list[dict], max_chars: int = 140) -> tuple[str, list[dict]]:
    if len(content) <= max_chars:
        return content, highlights

    prefix = ""
    suffix = ""
    if highlights:
        first = highlights[0]
        start = max(0, first["start"] - 48)
        end = min(len(content), start + max_chars)
        if start > 0:
            prefix = "..."
        if end < len(content):
            suffix = "..."
        preview = prefix + content[start:end] + suffix
        adjusted = []
        for item in highlights:
            if item["end"] <= start or item["start"] >= end:
                continue
            adjusted.append(
                {
                    "start": max(item["start"], start) - start + len(prefix),
                    "end": min(item["end"], end) - start + len(prefix),
                }
            )
        return preview, adjusted

    preview = content[:max_chars]
    if max_chars < len(content):
        preview += "..."
    return preview, []


def _load_search_chunks(row) -> list[dict]:
    file_hash = row["file_hash"]
    if file_hash:
        elements = load_cached(file_hash)
        if elements:
            return build_structured_chunks(elements)

    full_text = (row["full_text"] or "").strip()
    if full_text:
        return _fallback_text_chunks(full_text)

    abstract = (row["abstract"] or "").strip()
    if abstract:
        return [
            {
                "chunk_index": -1,
                "content": abstract,
                "heading": "Abstract",
                "page_number": 0,
                "element_type": "abstract",
            }
        ]

    return []


def _fallback_text_chunks(text: str, chunk_size: int = 500) -> list[dict]:
    paragraphs = [part.strip() for part in text.split("\n") if part.strip()]
    chunks: list[dict] = []
    buffer = ""
    chunk_index = 0

    for paragraph in paragraphs:
        if buffer and len(buffer) + len(paragraph) > chunk_size:
            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "content": buffer,
                    "heading": "",
                    "page_number": 0,
                    "element_type": "paragraph",
                }
            )
            chunk_index += 1
            buffer = paragraph
        else:
            buffer = f"{buffer}\n{paragraph}".strip() if buffer else paragraph

    if buffer:
        chunks.append(
            {
                "chunk_index": chunk_index,
                "content": buffer,
                "heading": "",
                "page_number": 0,
                "element_type": "paragraph",
            }
        )

    return chunks
