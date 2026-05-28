"""Citation formatting engine using CSL."""

from __future__ import annotations

import json
import re
from pathlib import Path

from backend.config import STYLES_DIR
from backend.db.sqlite import get_connection

# Citation pattern: [@citekey] or [@key1; @key2]
CITATION_PATTERN = re.compile(r'\[@([^\]]+)\]')


def extract_citations_from_text(text: str) -> list[str]:
    """Extract all citation keys from markdown text."""
    keys = []
    for match in CITATION_PATTERN.finditer(text):
        group = match.group(1)
        # Split multiple citations: @key1; @key2
        for part in group.split(";"):
            part = part.strip()
            if part.startswith("@"):
                part = part[1:]
            if part:
                keys.append(part)
    return keys


def get_literature_csl_json(cite_keys: list[str]) -> list[dict]:
    """Convert literature records to CSL-JSON format."""
    conn = get_connection()
    csl_items = []

    for key in cite_keys:
        row = conn.execute(
            "SELECT * FROM literature WHERE cite_key = ?", (key,)
        ).fetchone()
        if not row:
            continue

        authors_raw = json.loads(row["authors"]) if row["authors"] else []
        csl_authors = []
        for a in authors_raw:
            csl_authors.append({
                "family": a.get("family", ""),
                "given": a.get("given", ""),
            })

        item = {
            "id": row["cite_key"],
            "type": "article-journal",
            "title": row["title"],
            "author": csl_authors,
            "container-title": row["journal"] or "",
            "volume": row["volume"] or "",
            "issue": row["issue"] or "",
            "page": row["pages"] or "",
            "DOI": row["doi"] or "",
            "PMID": row["pmid"] or "",
            "publisher": row["publisher"] or "",
            "abstract": row["abstract"] or "",
        }

        if row["year"]:
            item["issued"] = {"date-parts": [[row["year"]]]}

        # Map type
        lit_type = row["type"]
        type_map = {
            "journal_article": "article-journal",
            "book_chapter": "chapter",
            "conference": "paper-conference",
            "thesis": "thesis",
            "report": "report",
        }
        item["type"] = type_map.get(lit_type, "article-journal")

        csl_items.append(item)

    return csl_items


def list_available_styles() -> list[dict]:
    """List available CSL style files."""
    styles = []
    for f in STYLES_DIR.glob("*.csl"):
        styles.append({
            "id": f.stem,
            "name": f.stem.replace("-", " ").title(),
            "path": str(f),
        })
    return styles


def export_bibtex(cite_keys: list[str] | None = None) -> str:
    """Export literature records as BibTeX format."""
    conn = get_connection()

    if cite_keys:
        placeholders = ",".join("?" * len(cite_keys))
        rows = conn.execute(
            f"SELECT * FROM literature WHERE cite_key IN ({placeholders})",
            cite_keys,
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM literature").fetchall()

    entries = []
    for row in rows:
        authors_raw = json.loads(row["authors"]) if row["authors"] else []
        author_str = " and ".join(
            f"{a.get('family', '')}, {a.get('given', '')}" for a in authors_raw
        )

        entry = f"@article{{{row['cite_key']},\n"
        entry += f"  title = {{{row['title']}}},\n"
        if author_str:
            entry += f"  author = {{{author_str}}},\n"
        if row["journal"]:
            entry += f"  journal = {{{row['journal']}}},\n"
        if row["year"]:
            entry += f"  year = {{{row['year']}}},\n"
        if row["volume"]:
            entry += f"  volume = {{{row['volume']}}},\n"
        if row["issue"]:
            entry += f"  number = {{{row['issue']}}},\n"
        if row["pages"]:
            entry += f"  pages = {{{row['pages']}}},\n"
        if row["doi"]:
            entry += f"  doi = {{{row['doi']}}},\n"
        if row["pmid"]:
            entry += f"  pmid = {{{row['pmid']}}},\n"
        if row["abstract"]:
            entry += f"  abstract = {{{row['abstract']}}},\n"
        entry += "}\n"
        entries.append(entry)

    return "\n".join(entries)


def export_csl_json(cite_keys: list[str] | None = None) -> str:
    """Export literature records as CSL-JSON."""
    if cite_keys:
        items = get_literature_csl_json(cite_keys)
    else:
        conn = get_connection()
        all_keys = [
            r["cite_key"]
            for r in conn.execute("SELECT cite_key FROM literature").fetchall()
        ]
        items = get_literature_csl_json(all_keys)
    return json.dumps(items, ensure_ascii=False, indent=2)
