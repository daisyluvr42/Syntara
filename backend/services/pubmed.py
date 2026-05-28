"""PubMed E-utilities integration with advanced search support."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import httpx

from backend.config import PUBMED_API_KEY, PUBMED_BASE_URL

# ---------------------------------------------------------------------------
# Field tag mapping: human-readable name -> PubMed search tag
# Mirrors the Advanced Search Builder dropdown on pubmed.ncbi.nlm.nih.gov
# ---------------------------------------------------------------------------
FIELD_TAGS: dict[str, str] = {
    "All Fields": "",
    "Affiliation": "[ad]",
    "Author": "[au]",
    "Author - Corporate": "[cn]",
    "Author - First": "[1au]",
    "Author - Identifier": "[auid]",
    "Author - Last": "[lastau]",
    "Book": "[book]",
    "Conflict of Interest Statements": "[cois]",
    "Date - Completion": "[dcom]",
    "Date - Create": "[crdt]",
    "Date - Entry": "[edat]",
    "Date - MeSH": "[mhda]",
    "Date - Modification": "[lr]",
    "Date - Publication": "[dp]",
    "EC/RN Number": "[rn]",
    "Editor": "[ed]",
    "Filter": "[filter]",
    "Grants and Funding": "[gr]",
    "ISBN": "[isbn]",
    "Investigator": "[ir]",
    "Issue": "[ip]",
    "Journal": "[ta]",
    "Language": "[la]",
    "Location ID": "[lid]",
    "MeSH Major Topic": "[majr]",
    "MeSH Subheading": "[sh]",
    "MeSH Terms": "[mh]",
    "Other Term": "[ot]",
    "Pagination": "[pg]",
    "Pharmacological Action": "[pa]",
    "Publication Type": "[pt]",
    "Publisher": "[pubn]",
    "Secondary Source ID": "[si]",
    "Subject - Personal Name": "[ps]",
    "Supplementary Concept": "[nm]",
    "Text Word": "[tw]",
    "Title": "[ti]",
    "Title/Abstract": "[tiab]",
    "Transliterated Title": "[tt]",
    "Volume": "[vi]",
}

SORT_OPTIONS: dict[str, str] = {
    "Best Match": "relevance",
    "Most Recent": "most+recent",
    "Publication Date": "pub+date",
    "First Author": "Author",
    "Journal": "JournalName",
    "Title": "title",
}


def build_query(
    terms: list[dict[str, str]] | None = None,
    raw_query: str | None = None,
) -> str:
    """Build a PubMed query string.

    Supports two modes:
    1. Structured terms: list of {term, field, op} dicts assembled via the
       Advanced Search Builder UI.  ``op`` is the Boolean joining this term
       to the *previous* one (AND / OR / NOT).  The first term's ``op`` is
       ignored.
    2. Raw query: a pre-composed query string typed directly into the query
       box (expert mode).

    If *both* are supplied, ``raw_query`` takes precedence.
    """
    if raw_query and raw_query.strip():
        return raw_query.strip()

    if not terms:
        return ""

    parts: list[str] = []
    for i, t in enumerate(terms):
        value = t.get("term", "").strip()
        if not value:
            continue
        field = t.get("field", "All Fields")
        tag = FIELD_TAGS.get(field, "")

        # Wrap multi-word values in quotes when a field tag is applied
        if tag and " " in value and not value.startswith('"'):
            fragment = f'"{value}"{tag}'
        elif tag:
            fragment = f"{value}{tag}"
        else:
            fragment = value

        if i == 0 or not parts:
            parts.append(fragment)
        else:
            op = t.get("op", "AND").upper()
            if op not in ("AND", "OR", "NOT"):
                op = "AND"
            parts.append(f"{op} {fragment}")

    return " ".join(parts)


async def search_pubmed(
    query: str,
    max_results: int = 20,
    sort: str = "relevance",
    page: int = 1,
    date_type: str | None = None,
    min_date: str | None = None,
    max_date: str | None = None,
    rel_date: int | None = None,
) -> dict[str, Any]:
    """Search PubMed and return PMIDs plus total count.

    Returns ``{"pmids": [...], "count": N, "retstart": M}``
    """
    retstart = (page - 1) * max_results

    params: dict[str, Any] = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retstart": retstart,
        "retmode": "json",
        "sort": sort,
    }
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY

    # Date filtering
    if date_type and (min_date or max_date or rel_date):
        params["datetype"] = date_type
        if rel_date is not None:
            params["reldate"] = rel_date
        else:
            if min_date:
                params["mindate"] = min_date
            if max_date:
                params["maxdate"] = max_date

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{PUBMED_BASE_URL}/esearch.fcgi", params=params)
        resp.raise_for_status()
        data = resp.json()

    result = data.get("esearchresult", {})
    pmids = result.get("idlist", [])
    count = int(result.get("count", 0))
    query_translation = result.get("querytranslation", "")

    return {
        "pmids": pmids,
        "count": count,
        "retstart": retstart,
        "query_translation": query_translation,
    }


async def fetch_pubmed_metadata(pmids: list[str]) -> list[dict]:
    """Fetch metadata for a list of PMIDs using efetch."""
    if not pmids:
        return []

    params: dict[str, Any] = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{PUBMED_BASE_URL}/efetch.fcgi", params=params)
        resp.raise_for_status()
        return _parse_pubmed_xml(resp.text)


def _parse_pubmed_xml(xml_text: str) -> list[dict]:
    """Parse PubMed efetch XML into metadata dicts."""
    results = []
    root = ET.fromstring(xml_text)

    for article_elem in root.findall(".//PubmedArticle"):
        medline = article_elem.find("MedlineCitation")
        if medline is None:
            continue

        article = medline.find("Article")
        if article is None:
            continue

        # PMID
        pmid_elem = medline.find("PMID")
        pmid = pmid_elem.text if pmid_elem is not None else ""

        # Title
        title_elem = article.find("ArticleTitle")
        title = "".join(title_elem.itertext()) if title_elem is not None else ""

        # Abstract
        abstract_parts = []
        abstract_elem = article.find("Abstract")
        if abstract_elem is not None:
            for at in abstract_elem.findall("AbstractText"):
                label = at.get("Label", "")
                text = "".join(at.itertext())
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
        abstract = " ".join(abstract_parts)

        # Authors
        authors = []
        author_list = article.find("AuthorList")
        if author_list is not None:
            for a in author_list.findall("Author"):
                family = a.findtext("LastName", "")
                given = a.findtext("ForeName", "")
                authors.append({"family": family, "given": given})

        # Journal
        journal_elem = article.find("Journal")
        journal = ""
        volume = None
        issue = None
        year = None
        if journal_elem is not None:
            journal_title = journal_elem.find("Title")
            journal = journal_title.text if journal_title is not None else ""
            ji = journal_elem.find("JournalIssue")
            if ji is not None:
                vol = ji.find("Volume")
                volume = vol.text if vol is not None else None
                iss = ji.find("Issue")
                issue = iss.text if iss is not None else None
                pub_date = ji.find("PubDate")
                if pub_date is not None:
                    y = pub_date.find("Year")
                    if y is not None:
                        try:
                            year = int(y.text)
                        except (ValueError, TypeError):
                            pass

        # Publication type
        pub_types = []
        for pt in article.findall("PublicationTypeList/PublicationType"):
            if pt.text:
                pub_types.append(pt.text)

        # Language
        lang_elem = article.find("Language")
        language = lang_elem.text if lang_elem is not None else None

        # Pages
        pages_elem = article.find("Pagination/MedlinePgn")
        pages = pages_elem.text if pages_elem is not None else None

        # DOI
        doi = None
        article_data = article_elem.find("PubmedData")
        if article_data is not None:
            for aid in article_data.findall(".//ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = aid.text
                    break

        # PMCID
        pmcid = None
        if article_data is not None:
            for aid in article_data.findall(".//ArticleId"):
                if aid.get("IdType") == "pmc":
                    pmcid = aid.text
                    break

        # Keywords
        keywords = []
        kw_list = medline.find("KeywordList")
        if kw_list is not None:
            for kw in kw_list.findall("Keyword"):
                if kw.text:
                    keywords.append(kw.text)

        # MeSH terms
        mesh_terms = []
        mesh_list = medline.find("MeshHeadingList")
        if mesh_list is not None:
            for mh in mesh_list.findall("MeshHeading"):
                desc = mh.find("DescriptorName")
                if desc is not None and desc.text:
                    major = desc.get("MajorTopicYN", "N")
                    mesh_terms.append({"term": desc.text, "major": major == "Y"})

        results.append({
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "journal": journal,
            "volume": volume,
            "issue": issue,
            "pages": pages,
            "year": year,
            "doi": doi,
            "pmid": pmid,
            "pmcid": pmcid,
            "keywords": keywords,
            "mesh_terms": mesh_terms,
            "pub_types": pub_types,
            "language": language,
            "type": "journal_article",
            "source": "pubmed",
        })

    return results


async def get_pmc_pdf_url(pmcid: str) -> str | None:
    """Try to get PDF download URL from PMC OA API."""
    if not pmcid:
        return None
    url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmcid}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url)
            root = ET.fromstring(resp.text)
            link = root.find(".//link[@format='pdf']")
            if link is not None:
                return link.get("href")
        except Exception:
            pass
    return None
