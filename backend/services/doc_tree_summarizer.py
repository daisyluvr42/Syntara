"""Bottom-up LLM summarization of document tree nodes.

After a tree is built from structured elements, this service generates
concise summaries for each interior node by summarizing its children's
content (leaf) or summaries (interior). This enables the navigator to
make informed choices at each level without reading full text.

Traversal: post-order (leaves first, then interior, then root).
LLM calls: one per interior node.
"""

from __future__ import annotations

import logging

from backend.models.doc_tree import DocTree, DocTreeNode
from backend.services.ai_provider import chat_completion
from backend.services.doc_tree_cache import save_tree

logger = logging.getLogger(__name__)

# Maximum content sent per summarization call (chars)
_MAX_INPUT_LEN = 3000

_SUMMARIZE_SYSTEM = (
    "You are a research document analyzer. Generate a concise summary "
    "(2-4 sentences) of the section content below. Focus on key topics, "
    "methods, findings, or arguments. Do NOT add any preamble or labels — "
    "just output the summary text directly."
)


async def summarize_tree(
    tree: DocTree,
    provider_id: str | None = None,
) -> DocTree:
    """Generate summaries for all interior nodes of the tree (bottom-up).

    Modifies the tree in-place and persists it.
    """
    count = await _summarize_node(tree.root, provider_id)
    tree.summaries_generated = True
    save_tree(tree)
    logger.info(
        "Tree summarization complete for '%s': %d nodes summarized",
        tree.title[:50],
        count,
    )
    return tree


async def _summarize_node(node: DocTreeNode, provider_id: str | None) -> int:
    """Recursively summarize a node's subtree. Returns count of nodes summarized."""
    if node.is_leaf:
        # Leaf nodes don't need LLM summaries — their content IS the text
        return 0

    # First, ensure all children are summarized
    count = 0
    for child in node.children:
        count += await _summarize_node(child, provider_id)

    # Build input for this interior node from children
    child_texts: list[str] = []
    for child in node.children:
        if child.is_leaf:
            text = child.content[:_MAX_INPUT_LEN]
        else:
            # Use child's summary if available, fall back to title
            text = child.summary or child.title
        label = f"[{child.title}]" if child.title != node.title else ""
        child_texts.append(f"{label}\n{text}" if label else text)

    combined = "\n\n---\n\n".join(child_texts)

    # Truncate if still too long
    if len(combined) > _MAX_INPUT_LEN:
        combined = combined[:_MAX_INPUT_LEN] + "\n...(truncated)"

    # LLM call
    messages = [
        {"role": "system", "content": _SUMMARIZE_SYSTEM},
        {
            "role": "user",
            "content": f"Section: {node.title}\nPage range: {node.page_start}-{node.page_end}\n\nContent:\n{combined}",
        },
    ]

    try:
        summary = await chat_completion(provider_id, messages, max_tokens=300, temperature=0.3)
        node.summary = summary.strip()
        count += 1
        logger.debug("Summarized node '%s' (%d chars)", node.title[:40], len(node.summary))
    except Exception as e:
        logger.warning("Failed to summarize node '%s': %s", node.title[:40], e)
        # Fallback: concatenate child titles
        node.summary = f"Contains: {', '.join(c.title for c in node.children[:5])}"
        count += 1

    return count
