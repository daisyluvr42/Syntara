"""Export API router (Markdown, Word, PDF, HTML, BibTeX)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from backend.db.sqlite import get_connection
from backend.services.citation_engine import (
    export_bibtex,
    export_csl_json,
    extract_citations_from_text,
    list_available_styles,
)
from backend.services.exporter import export_markdown_with_references
from backend.services.pandoc import export_document, get_pandoc_version, is_pandoc_available

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/styles")
async def get_styles():
    """List available CSL styles."""
    return list_available_styles()


@router.get("/pandoc-status")
async def pandoc_status():
    """Check Pandoc availability."""
    available = is_pandoc_available()
    version = get_pandoc_version() if available else None
    return {"available": available, "version": version}


@router.post("/markdown/{doc_id}")
async def export_md(doc_id: str, csl_style: str = "vancouver"):
    """Export document as formatted Markdown with references."""
    conn = get_connection()
    row = conn.execute("SELECT content, csl_style FROM document WHERE id = ?", (doc_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Document not found")

    style = csl_style or row["csl_style"]
    result = export_markdown_with_references(row["content"], style)
    return Response(content=result, media_type="text/markdown",
                    headers={"Content-Disposition": "attachment; filename=export.md"})


@router.post("/docx/{doc_id}")
async def export_docx(doc_id: str, csl_style: str = "vancouver", template: str | None = None):
    """Export document as Word (.docx) via Pandoc."""
    content = _get_doc_content(doc_id)
    try:
        data = export_document(content, "docx", csl_style, template)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": "attachment; filename=export.docx"},
        )
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.post("/pdf/{doc_id}")
async def export_pdf(doc_id: str, csl_style: str = "vancouver"):
    """Export document as PDF via Pandoc."""
    content = _get_doc_content(doc_id)
    try:
        data = export_document(content, "pdf", csl_style)
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=export.pdf"},
        )
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.post("/html/{doc_id}")
async def export_html(doc_id: str, csl_style: str = "vancouver"):
    """Export document as HTML via Pandoc."""
    content = _get_doc_content(doc_id)
    try:
        data = export_document(content, "html", csl_style)
        return Response(content=data, media_type="text/html",
                        headers={"Content-Disposition": "attachment; filename=export.html"})
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.post("/latex/{doc_id}")
async def export_latex(doc_id: str, csl_style: str = "vancouver"):
    """Export document as LaTeX via Pandoc."""
    content = _get_doc_content(doc_id)
    try:
        data = export_document(content, "latex", csl_style)
        return Response(content=data, media_type="application/x-latex",
                        headers={"Content-Disposition": "attachment; filename=export.tex"})
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.get("/bibtex")
async def export_bib(cite_keys: str = Query(default="")):
    """Export literature as BibTeX. Pass comma-separated cite_keys or empty for all."""
    keys = [k.strip() for k in cite_keys.split(",") if k.strip()] if cite_keys else None
    bib = export_bibtex(keys)
    return Response(content=bib, media_type="application/x-bibtex",
                    headers={"Content-Disposition": "attachment; filename=references.bib"})


@router.get("/csl-json")
async def export_csl(cite_keys: str = Query(default="")):
    """Export literature as CSL-JSON."""
    keys = [k.strip() for k in cite_keys.split(",") if k.strip()] if cite_keys else None
    data = export_csl_json(keys)
    return Response(content=data, media_type="application/json",
                    headers={"Content-Disposition": "attachment; filename=references.json"})


def _get_doc_content(doc_id: str) -> str:
    conn = get_connection()
    row = conn.execute("SELECT content FROM document WHERE id = ?", (doc_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Document not found")
    return row["content"]
