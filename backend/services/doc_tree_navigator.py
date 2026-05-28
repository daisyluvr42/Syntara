"""LLM-guided tree navigation for precise context retrieval.

Given a user query and a document tree (with summaries), the navigator
descends the tree level-by-level, asking the LLM at each level which
children are relevant. This yields precise leaf-level content without
embedding the entire document.

Beam search: at each level, keep top-B branches (default B=2).
Typical cost: 2-3 LLM calls per document.
"""

from __future__ import annotations

import json
import logging
import re

from backend.models.doc_tree import DocTree, DocTreeNode
from backend.services.ai_provider import chat_completion

logger = logging.getLogger(__name__)

_NAVIGATE_SYSTEM = (
    "You are a research document navigator. Given a query and a list of "
    "document sections with their summaries, select the sections most likely "
    "to contain relevant information.\n\n"
    "Respond with ONLY a JSON array of section indices (0-based). "
    "Select at most {beam_width} sections. Example: [0, 2]\n"
    "If none are relevant, respond with an empty array: []"
)


async def navigate_tree(
    tree: DocTree,
    query: str,
    beam_width: int = 2,
    provider_id: str | None = None,
) -> list[DocTreeNode]:
    """Navigate the document tree to find leaf nodes relevant to the query.

    Args:
        tree: Document tree with summaries.
        query: User's search query.
        beam_width: Max branches to keep at each level.
        provider_id: AI provider to use for navigation.

    Returns:
        List of relevant leaf nodes with their content.
    """
    if not tree.root.children:
        # Flat document — return root content if any
        return tree.root.leaf_nodes()[:beam_width]

    # Start navigation from root's children
    current_nodes = tree.root.children
    depth = 0
    max_depth = 5  # safety limit

    while depth < max_depth:
        depth += 1

        # If all current nodes are leaves, we're done
        if all(n.is_leaf for n in current_nodes):
            break

        # If few enough nodes, don't bother navigating — take them all
        if len(current_nodes) <= beam_width:
            # Expand: replace interior nodes with their children
            next_nodes = []
            for n in current_nodes:
                if n.is_leaf:
                    next_nodes.append(n)
                else:
                    next_nodes.extend(n.children)
            current_nodes = next_nodes
            continue

        # LLM navigation: ask which sections are relevant
        selected_indices = await _select_relevant_children(
            query, current_nodes, beam_width, provider_id
        )

        if not selected_indices:
            # LLM found nothing relevant — stop here
            logger.debug("Navigator found no relevant sections at depth %d", depth)
            break

        # Expand selected nodes
        next_nodes = []
        for idx in selected_indices:
            if idx < len(current_nodes):
                node = current_nodes[idx]
                if node.is_leaf:
                    next_nodes.append(node)
                else:
                    next_nodes.extend(node.children)

        if not next_nodes:
            break

        current_nodes = next_nodes

    # Collect leaves from remaining nodes
    leaves: list[DocTreeNode] = []
    for n in current_nodes:
        if n.is_leaf:
            leaves.append(n)
        else:
            leaves.extend(n.leaf_nodes()[:beam_width])

    logger.info(
        "Tree navigation for '%s' in '%s': %d leaves found in %d steps",
        query[:50],
        tree.title[:30],
        len(leaves),
        depth,
    )
    return leaves


async def _select_relevant_children(
    query: str,
    nodes: list[DocTreeNode],
    beam_width: int,
    provider_id: str | None,
) -> list[int]:
    """Ask LLM to select relevant sections from a list of nodes."""
    # Build section descriptions
    section_descs = []
    for i, node in enumerate(nodes):
        desc = f"[{i}] {node.title}"
        if node.summary:
            desc += f"\n    Summary: {node.summary}"
        elif node.is_leaf and node.content:
            preview = node.content[:200].replace("\n", " ")
            desc += f"\n    Preview: {preview}..."
        if node.page_start:
            desc += f"\n    Pages: {node.page_start}-{node.page_end}"
        section_descs.append(desc)

    sections_text = "\n\n".join(section_descs)

    messages = [
        {
            "role": "system",
            "content": _NAVIGATE_SYSTEM.format(beam_width=beam_width),
        },
        {
            "role": "user",
            "content": f"Query: {query}\n\nAvailable sections:\n\n{sections_text}",
        },
    ]

    try:
        response = await chat_completion(
            provider_id, messages, max_tokens=100, temperature=0.1
        )
        indices = _parse_index_response(response, len(nodes))
        logger.debug(
            "Navigator selected indices %s from %d sections",
            indices,
            len(nodes),
        )
        return indices[:beam_width]
    except Exception as e:
        logger.warning("Navigator LLM call failed: %s", e)
        # Fallback: return first beam_width indices
        return list(range(min(beam_width, len(nodes))))


def _parse_index_response(response: str, max_index: int) -> list[int]:
    """Parse LLM response to extract selected indices."""
    # Try JSON array parsing first
    response = response.strip()

    # Extract JSON array from response (might have surrounding text)
    match = re.search(r'\[[\d\s,]*\]', response)
    if match:
        try:
            indices = json.loads(match.group())
            return [i for i in indices if isinstance(i, int) and 0 <= i < max_index]
        except json.JSONDecodeError:
            pass

    # Fallback: extract individual numbers
    numbers = re.findall(r'\b(\d+)\b', response)
    return [int(n) for n in numbers if 0 <= int(n) < max_index]
