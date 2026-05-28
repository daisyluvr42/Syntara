"""Document export service (MD + CSL formatting)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from backend.services.citation_engine import (
    CITATION_PATTERN,
    extract_citations_from_text,
    export_bibtex,
    get_literature_csl_json,
)

# Marker embedded at end of References to allow reversibility
_MAP_PATTERN = re.compile(r'<!-- citation-map: ({.*?}) -->')
# Matches numbered inline refs like [1], [1,2], [1,2,3]
_NUM_REF_PATTERN = re.compile(r'\[(\d+(?:,\s*\d+)*)\]')
# Matches APA-style inline refs like (Author, 2024) or (Author1 & Author2, 2024)
_APA_REF_PATTERN = re.compile(r'\(([A-Z][a-z]+(?:\s(?:&|et al\.)\s[A-Z][a-z]+)?,\s\d{4}(?:;\s[A-Z][a-z]+(?:\s(?:&|et al\.)\s[A-Z][a-z]+)?,\s\d{4})*)\)')
# References section header
_REF_HEADER = re.compile(r'\n+##\s+References\b.*', re.DOTALL)


def export_markdown_with_references(
    content: str,
    csl_style: str = "vancouver",
) -> str:
    """
    Export markdown with formatted references.
    Replaces [@citekey] markers with numbered references and appends bibliography.
    """
    cite_keys = extract_citations_from_text(content)
    if not cite_keys:
        return content

    unique_keys = list(dict.fromkeys(cite_keys))  # preserve order, deduplicate
    csl_items = get_literature_csl_json(unique_keys)

    # Build key -> number mapping
    key_to_num = {k: i + 1 for i, k in enumerate(unique_keys)}

    # Replace citation markers in text
    def replace_citation(match):
        group = match.group(1)
        parts = [p.strip().lstrip("@") for p in group.split(";")]
        nums = []
        for p in parts:
            if p in key_to_num:
                nums.append(str(key_to_num[p]))
        return f"[{','.join(nums)}]" if nums else match.group(0)

    formatted = re.sub(r'\[@([^\]]+)\]', replace_citation, content)

    # Generate reference list
    ref_lines = ["\n\n## References\n"]
    for item in csl_items:
        key = item["id"]
        num = key_to_num.get(key, 0)
        authors = item.get("author", [])
        author_str = _format_authors(authors)
        title = item.get("title", "")
        journal = item.get("container-title", "")
        year = ""
        if item.get("issued") and item["issued"].get("date-parts"):
            year = str(item["issued"]["date-parts"][0][0])
        volume = item.get("volume", "")
        issue = item.get("issue", "")
        pages = item.get("page", "")
        doi = item.get("DOI", "")

        ref = f"{num}. {author_str}. {title}."
        if journal:
            ref += f" *{journal}*."
        if year:
            ref += f" {year}"
        if volume:
            ref += f";{volume}"
        if issue:
            ref += f"({issue})"
        if pages:
            ref += f":{pages}"
        ref += "."
        if doi:
            ref += f" doi:{doi}"

        ref_lines.append(ref)

    formatted += "\n".join(ref_lines)
    return formatted


def _format_authors(authors: list[dict], max_authors: int = 3) -> str:
    """Format author list for reference (Vancouver style: Family AB)."""
    if not authors:
        return ""
    names = []
    for a in authors[:max_authors]:
        family = a.get("family", "")
        given = a.get("given", "")
        initials = "".join(w[0].upper() for w in given.split() if w) if given else ""
        names.append(f"{family} {initials}".strip())
    result = ", ".join(names)
    if len(authors) > max_authors:
        result += ", et al"
    return result


def _format_authors_apa(authors: list[dict]) -> str:
    """Format author list for APA reference: Family, A. B., & Family, C. D."""
    if not authors:
        return ""
    names = []
    for a in authors[:7]:
        family = a.get("family", "")
        given = a.get("given", "")
        initials = ". ".join(w[0].upper() for w in given.split() if w) + "." if given else ""
        names.append(f"{family}, {initials}".strip(", "))
    if len(authors) > 7:
        return ", ".join(names[:6]) + ", ... " + names[-1]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + ", & " + names[-1]


def _format_authors_gb(authors: list[dict]) -> str:
    """Format author list for GB/T 7714: Family Given, Family Given."""
    if not authors:
        return ""
    names = []
    for a in authors[:3]:
        family = a.get("family", "")
        given = a.get("given", "")
        names.append(f"{family} {given}".strip())
    result = ", ".join(names)
    if len(authors) > 3:
        result += ", 等"
    return result


def _apa_inline(authors: list[dict], year: int | None) -> str:
    """Build APA inline citation text: Author (Year) / Author1 & Author2 (Year)."""
    yr = str(year) if year else "n.d."
    if not authors:
        return yr
    if len(authors) == 1:
        return f"{authors[0].get('family', '?')}, {yr}"
    if len(authors) == 2:
        return f"{authors[0].get('family', '?')} & {authors[1].get('family', '?')}, {yr}"
    return f"{authors[0].get('family', '?')} et al., {yr}"


# ---------------------------------------------------------------------------
# Reversible citation formatting
# ---------------------------------------------------------------------------

def revert_formatted_citations(content: str) -> str:
    """Restore [@citekey] markers from previously formatted content.

    Uses the citation-map comment at the end of the References section
    to reverse inline numbered/APA citations back to [@citekey] format.
    Also strips the References section.
    """
    map_match = _MAP_PATTERN.search(content)
    if not map_match:
        # No previous formatting — return as-is (strip any empty References section)
        return _REF_HEADER.sub("", content).rstrip()

    try:
        num_to_key: dict[str, str] = json.loads(map_match.group(1))
    except json.JSONDecodeError:
        return _REF_HEADER.sub("", content).rstrip()

    # Strip References section (including the map comment)
    body = _REF_HEADER.sub("", content).rstrip()

    # Revert numbered refs [1], [1,2] → [@key1], [@key1; @key2]
    def _revert_num(m: re.Match) -> str:
        nums = [n.strip() for n in m.group(1).split(",")]
        keys = [num_to_key.get(n) for n in nums]
        if all(keys):
            markers = "; ".join(f"@{k}" for k in keys)
            return f"[{markers}]"
        return m.group(0)  # can't revert — leave as-is

    body = _NUM_REF_PATTERN.sub(_revert_num, body)

    return body


def format_citations(content: str, style: str = "vancouver") -> str:
    """Format all [@citekey] citations in content according to the given style.

    This is idempotent: if content was previously formatted, it reverts first
    then re-formats with the requested style. Stores a citation-map comment
    in the References section to enable future reversal.
    """
    # Step 1: Revert any existing formatting
    raw = revert_formatted_citations(content)

    # Step 2: Extract all cite keys from the raw content
    cite_keys = extract_citations_from_text(raw)
    if not cite_keys:
        return raw

    unique_keys = list(dict.fromkeys(cite_keys))
    csl_items = get_literature_csl_json(unique_keys)

    # Build key → number mapping
    key_to_num = {k: i + 1 for i, k in enumerate(unique_keys)}
    # Build key → CSL item lookup
    key_to_item = {item["id"]: item for item in csl_items}

    # Step 3: Replace inline citations
    if style == "apa":
        formatted = _format_inline_apa(raw, key_to_item)
    else:
        # Vancouver / GB/T 7714 both use numbered inline
        formatted = _format_inline_numbered(raw, key_to_num)

    # Step 4: Build references section
    ref_lines = ["\n\n## References\n"]
    for key in unique_keys:
        num = key_to_num[key]
        item = key_to_item.get(key)
        if not item:
            ref_lines.append(f"{num}. [{key}] — metadata not found")
            continue

        if style == "apa":
            ref_lines.append(_build_ref_apa(item, key))
        elif style == "gb-t-7714":
            ref_lines.append(_build_ref_gb(num, item))
        else:  # vancouver
            ref_lines.append(_build_ref_vancouver(num, item))

    # Step 5: Embed citation-map for reversibility
    num_to_key = {str(v): k for k, v in key_to_num.items()}
    map_comment = f"\n<!-- citation-map: {json.dumps(num_to_key, ensure_ascii=False)} -->"
    ref_lines.append(map_comment)

    formatted += "\n".join(ref_lines)
    return formatted


def _format_inline_numbered(raw: str, key_to_num: dict[str, int]) -> str:
    """Replace [@key1; @key2] with [1,2]."""
    def _replace(m: re.Match) -> str:
        group = m.group(1)
        parts = [p.strip().lstrip("@") for p in group.split(";")]
        nums = [str(key_to_num[p]) for p in parts if p in key_to_num]
        return f"[{','.join(nums)}]" if nums else m.group(0)
    return CITATION_PATTERN.sub(_replace, raw)


def _format_inline_apa(raw: str, key_to_item: dict[str, dict]) -> str:
    """Replace [@key1; @key2] with (Author1, Year; Author2, Year)."""
    def _replace(m: re.Match) -> str:
        group = m.group(1)
        parts = [p.strip().lstrip("@") for p in group.split(";")]
        inlines = []
        for p in parts:
            item = key_to_item.get(p)
            if item:
                authors = item.get("author", [])
                year = None
                if item.get("issued") and item["issued"].get("date-parts"):
                    year = item["issued"]["date-parts"][0][0]
                inlines.append(_apa_inline(authors, year))
            else:
                inlines.append(p)
        return f"({'; '.join(inlines)})" if inlines else m.group(0)
    return CITATION_PATTERN.sub(_replace, raw)


def _build_ref_vancouver(num: int, item: dict) -> str:
    """Build a single Vancouver-style reference line."""
    authors = _format_authors(item.get("author", []))
    title = item.get("title", "")
    journal = item.get("container-title", "")
    year = ""
    if item.get("issued") and item["issued"].get("date-parts"):
        year = str(item["issued"]["date-parts"][0][0])
    volume = item.get("volume", "")
    issue = item.get("issue", "")
    pages = item.get("page", "")
    doi = item.get("DOI", "")

    ref = f"{num}. {authors}. {title}."
    if journal:
        ref += f" *{journal}*."
    if year:
        ref += f" {year}"
    if volume:
        ref += f";{volume}"
    if issue:
        ref += f"({issue})"
    if pages:
        ref += f":{pages}"
    ref += "."
    if doi:
        ref += f" doi:{doi}"
    return ref


def _build_ref_apa(item: dict, key: str) -> str:
    """Build a single APA 7th-style reference line."""
    authors = _format_authors_apa(item.get("author", []))
    title = item.get("title", "")
    journal = item.get("container-title", "")
    year = ""
    if item.get("issued") and item["issued"].get("date-parts"):
        year = str(item["issued"]["date-parts"][0][0])
    volume = item.get("volume", "")
    issue = item.get("issue", "")
    pages = item.get("page", "")
    doi = item.get("DOI", "")

    ref = f"{authors} ({year or 'n.d.'}). {title}."
    if journal:
        ref += f" *{journal}*"
        if volume:
            ref += f", *{volume}*"
        if issue:
            ref += f"({issue})"
        if pages:
            ref += f", {pages}"
        ref += "."
    if doi:
        ref += f" https://doi.org/{doi}"
    return ref


def _build_ref_gb(num: int, item: dict) -> str:
    """Build a single GB/T 7714-style reference line."""
    authors = _format_authors_gb(item.get("author", []))
    title = item.get("title", "")
    journal = item.get("container-title", "")
    year = ""
    if item.get("issued") and item["issued"].get("date-parts"):
        year = str(item["issued"]["date-parts"][0][0])
    volume = item.get("volume", "")
    issue = item.get("issue", "")
    pages = item.get("page", "")
    doi = item.get("DOI", "")

    ref = f"[{num}] {authors}. {title}[J]."
    if journal:
        ref += f" {journal}"
    if year:
        ref += f", {year}"
    if volume:
        ref += f", {volume}"
    if issue:
        ref += f"({issue})"
    if pages:
        ref += f": {pages}"
    ref += "."
    if doi:
        ref += f" DOI:{doi}"
    return ref
