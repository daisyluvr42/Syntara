"""CrossRef API integration for metadata retrieval."""

from __future__ import annotations

import httpx

from backend.config import CROSSREF_BASE_URL, CROSSREF_MAILTO


async def fetch_metadata_by_doi(doi: str) -> dict | None:
    """Fetch structured metadata from CrossRef by DOI."""
    url = f"{CROSSREF_BASE_URL}/{doi}"
    headers = {}
    if CROSSREF_MAILTO:
        headers["mailto"] = CROSSREF_MAILTO

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return _parse_crossref_response(data)
        except Exception:
            return None


def _parse_crossref_response(data: dict) -> dict:
    """Parse CrossRef API response into our metadata format."""
    msg = data.get("message", {})

    authors = []
    for a in msg.get("author", []):
        authors.append({
            "family": a.get("family", ""),
            "given": a.get("given", ""),
            "affiliation": (a.get("affiliation", [{}])[0].get("name", "")
                           if a.get("affiliation") else None),
        })

    title_list = msg.get("title", [])
    title = title_list[0] if title_list else ""

    # Extract year from date-parts
    year = None
    date_str = None
    date_parts = msg.get("published-print", msg.get("published-online", {}))
    if date_parts and date_parts.get("date-parts"):
        parts = date_parts["date-parts"][0]
        if parts:
            year = parts[0]
            if len(parts) >= 3:
                date_str = f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
            elif len(parts) >= 2:
                date_str = f"{parts[0]:04d}-{parts[1]:02d}"

    journal_list = msg.get("container-title", [])
    journal = journal_list[0] if journal_list else None

    issn_list = msg.get("ISSN", [])
    isbn_list = msg.get("ISBN", [])

    return {
        "title": title,
        "authors": authors,
        "abstract": msg.get("abstract", ""),
        "journal": journal,
        "publisher": msg.get("publisher", ""),
        "volume": msg.get("volume"),
        "issue": msg.get("issue"),
        "pages": msg.get("page"),
        "year": year,
        "date": date_str,
        "doi": msg.get("DOI"),
        "issn": issn_list[0] if issn_list else None,
        "isbn": isbn_list[0] if isbn_list else None,
        "type": _map_type(msg.get("type", "")),
        "keywords": msg.get("subject", []),
        "source": "crossref",
    }


def _map_type(crossref_type: str) -> str:
    mapping = {
        "journal-article": "journal_article",
        "book-chapter": "book_chapter",
        "proceedings-article": "conference",
        "dissertation": "thesis",
        "report": "report",
    }
    return mapping.get(crossref_type, "other")
