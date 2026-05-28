"""Persistent cache for document trees (PageIndex-style hierarchical structures).

Trees are stored as JSON files keyed by literature_id in data/doc_trees/.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from backend.config import DOC_TREE_DIR
from backend.models.doc_tree import DocTree

logger = logging.getLogger(__name__)


def _tree_path(literature_id: str) -> Path:
    return DOC_TREE_DIR / f"{literature_id}.json"


def load_tree(literature_id: str) -> DocTree | None:
    """Load a cached document tree. Returns None on miss."""
    path = _tree_path(literature_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        tree = DocTree.model_validate(data)
        logger.debug("Doc tree loaded: %s (%d nodes)", literature_id[:12], tree.node_count)
        return tree
    except (json.JSONDecodeError, OSError, Exception) as e:
        logger.warning("Doc tree cache corrupted for %s: %s", literature_id[:12], e)
        return None


def save_tree(tree: DocTree) -> None:
    """Persist a document tree to cache."""
    path = _tree_path(tree.literature_id)
    path.write_text(
        tree.model_dump_json(indent=2),
        encoding="utf-8",
    )
    size_kb = path.stat().st_size / 1024
    logger.info(
        "Doc tree saved: %s (%d nodes, %d leaves, %.1f KB)",
        tree.literature_id[:12],
        tree.node_count,
        tree.leaf_count,
        size_kb,
    )


def has_tree(literature_id: str) -> bool:
    return _tree_path(literature_id).exists()


def delete_tree(literature_id: str) -> None:
    _tree_path(literature_id).unlink(missing_ok=True)
    logger.info("Doc tree deleted: %s", literature_id[:12])


def list_trees() -> list[dict]:
    """List all cached trees with basic metadata."""
    items = []
    for path in sorted(DOC_TREE_DIR.glob("*.json")):
        lit_id = path.stem
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append({
                "literature_id": lit_id,
                "title": data.get("title", ""),
                "node_count": data.get("node_count", 0),
                "leaf_count": data.get("leaf_count", 0),
                "summaries_generated": data.get("summaries_generated", False),
                "size_bytes": path.stat().st_size,
            })
        except (json.JSONDecodeError, OSError):
            items.append({
                "literature_id": lit_id,
                "title": "?",
                "node_count": 0,
                "leaf_count": 0,
                "summaries_generated": False,
                "size_bytes": path.stat().st_size if path.exists() else 0,
            })
    return items
