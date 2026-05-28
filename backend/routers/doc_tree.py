"""Document tree management API router.

Provides endpoints to build, summarize, view, and delete document structure
trees used for PageIndex-style hierarchical RAG navigation.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db.sqlite import get_connection
from backend.services.doc_tree_builder import build_tree
from backend.services.doc_tree_cache import (
    delete_tree,
    has_tree,
    list_trees,
    load_tree,
    save_tree,
)
from backend.services.doc_tree_summarizer import summarize_tree
from backend.services.extract_cache import load_cached

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/doc-trees", tags=["doc-trees"])


class BuildRequest(BaseModel):
    provider_id: str | None = None
    auto_summarize: bool = False


class SummarizeRequest(BaseModel):
    provider_id: str | None = None


# =====================
# Fixed-path routes FIRST (before /{lit_id} to avoid shadowing)
# =====================

@router.get("")
async def list_doc_trees():
    """List all cached document trees with metadata."""
    trees = list_trees()

    # Enrich with literature titles from DB
    conn = get_connection()
    for t in trees:
        row = conn.execute(
            "SELECT title, cite_key FROM literature WHERE id = ?",
            (t["literature_id"],),
        ).fetchone()
        if row:
            t["lit_title"] = row["title"]
            t["cite_key"] = row["cite_key"]

    return {"items": trees, "total": len(trees)}


@router.get("/stats")
async def doc_tree_stats():
    """Get summary statistics for document trees."""
    trees = list_trees()
    total_size = sum(t["size_bytes"] for t in trees)
    summarized = sum(1 for t in trees if t["summaries_generated"])

    return {
        "total_trees": len(trees),
        "summarized": summarized,
        "unsummarized": len(trees) - summarized,
        "total_size_bytes": total_size,
        "total_nodes": sum(t["node_count"] for t in trees),
        "total_leaves": sum(t["leaf_count"] for t in trees),
    }


@router.delete("")
async def clear_all_trees(confirm: bool = False):
    """Delete all document trees."""
    if not confirm:
        raise HTTPException(400, "Pass confirm=true to clear all trees")

    trees = list_trees()
    for t in trees:
        delete_tree(t["literature_id"])

    return {"ok": True, "deleted": len(trees)}


@router.post("/build-all")
async def build_all_trees(req: BuildRequest = BuildRequest()):
    """Build document trees for all literature entries that have extracted elements."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, file_hash FROM literature WHERE file_hash IS NOT NULL"
    ).fetchall()

    built = 0
    skipped = 0
    errors = 0

    for row in rows:
        lit_id = row["id"]

        # Skip if tree already exists
        if has_tree(lit_id):
            skipped += 1
            continue

        file_hash = row["file_hash"]
        elements = load_cached(file_hash)
        if elements is None:
            skipped += 1
            continue

        try:
            tree = build_tree(lit_id, row["title"], elements)
            save_tree(tree)

            if req.auto_summarize:
                await summarize_tree(tree, provider_id=req.provider_id)

            built += 1
        except Exception as e:
            logger.warning("Failed to build tree for %s: %s", lit_id[:12], e)
            errors += 1

    return {"built": built, "skipped": skipped, "errors": errors}


@router.post("/summarize-all")
async def summarize_all_trees(req: SummarizeRequest = SummarizeRequest()):
    """Run LLM summarization on all unsummarized trees."""
    trees = list_trees()
    summarized = 0
    errors = 0

    for t in trees:
        if t["summaries_generated"]:
            continue

        tree = load_tree(t["literature_id"])
        if not tree:
            continue

        try:
            await summarize_tree(tree, provider_id=req.provider_id)
            summarized += 1
        except Exception as e:
            logger.warning(
                "Failed to summarize tree for %s: %s",
                t["literature_id"][:12],
                e,
            )
            errors += 1

    return {"summarized": summarized, "errors": errors}


# =====================
# Parameterized routes (/{lit_id})
# =====================

@router.get("/{lit_id}")
async def get_doc_tree(lit_id: str, max_depth: int | None = None):
    """Get the full document tree for a literature entry."""
    tree = load_tree(lit_id)
    if not tree:
        raise HTTPException(404, "Document tree not found")

    result = tree.model_dump()

    # Optionally limit depth for preview
    if max_depth is not None:
        result["root"] = _prune_depth(result["root"], max_depth)

    return result


@router.post("/{lit_id}/build")
async def build_doc_tree(lit_id: str, req: BuildRequest = BuildRequest()):
    """Build a document structure tree for a literature entry.

    Uses the cached structured elements (ODL/OCR) to construct the hierarchy.
    Optionally runs LLM summarization immediately.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT id, title, file_hash FROM literature WHERE id = ?", (lit_id,)
    ).fetchone()
    if not row:
        raise HTTPException(404, "Literature not found")

    file_hash = row["file_hash"]
    if not file_hash:
        raise HTTPException(400, "Literature has no associated file")

    # Load structured elements from extract cache
    elements = load_cached(file_hash)
    if elements is None:
        raise HTTPException(
            400,
            "No extracted structured elements found. Import/process the PDF first.",
        )

    # Build tree
    tree = build_tree(lit_id, row["title"], elements)
    save_tree(tree)

    # Optional immediate summarization
    if req.auto_summarize:
        tree = await summarize_tree(tree, provider_id=req.provider_id)

    return {
        "literature_id": lit_id,
        "node_count": tree.node_count,
        "leaf_count": tree.leaf_count,
        "summaries_generated": tree.summaries_generated,
    }


@router.post("/{lit_id}/summarize")
async def summarize_doc_tree(lit_id: str, req: SummarizeRequest = SummarizeRequest()):
    """Run LLM summarization on an existing document tree."""
    tree = load_tree(lit_id)
    if not tree:
        raise HTTPException(404, "Document tree not found. Build it first.")

    if tree.summaries_generated:
        return {
            "literature_id": lit_id,
            "message": "Summaries already generated",
            "node_count": tree.node_count,
        }

    tree = await summarize_tree(tree, provider_id=req.provider_id)

    return {
        "literature_id": lit_id,
        "node_count": tree.node_count,
        "leaf_count": tree.leaf_count,
        "summaries_generated": True,
    }


@router.delete("/{lit_id}")
async def delete_doc_tree(lit_id: str):
    """Delete the document tree for a literature entry."""
    if not has_tree(lit_id):
        raise HTTPException(404, "Document tree not found")
    delete_tree(lit_id)
    return {"ok": True}


# --- Helpers ---

def _prune_depth(node_dict: dict, max_depth: int, current_depth: int = 0) -> dict:
    """Prune a tree dict to a maximum depth."""
    if current_depth >= max_depth:
        # Replace children with a count
        child_count = len(node_dict.get("children", []))
        node_dict["children"] = []
        node_dict["_pruned_children"] = child_count
        return node_dict

    node_dict["children"] = [
        _prune_depth(c, max_depth, current_depth + 1)
        for c in node_dict.get("children", [])
    ]
    return node_dict
