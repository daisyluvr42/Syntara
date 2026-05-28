"""Build document structure trees from extracted structured elements.

Uses the heading hierarchy from ODL / OCR extractions to construct a tree.
Zero LLM cost — purely structural parsing.

Algorithm:
  1. Start with a virtual root node (level 0).
  2. Walk through elements in document order.
  3. When a heading is encountered, pop the stack back to the parent level
     and create a new interior node.
  4. Non-heading elements (paragraphs, tables, etc.) accumulate as content
     in the current leaf-level bucket.
  5. After all elements are processed, flush remaining content into leaves.
"""

from __future__ import annotations

import logging

from backend.models.doc_tree import DocTree, DocTreeNode

logger = logging.getLogger(__name__)

# Maximum content length per leaf node (chars). Longer sections get split.
_MAX_LEAF_CONTENT = 2000


def build_tree(
    literature_id: str,
    title: str,
    structured_elements: list[dict],
) -> DocTree:
    """Build a hierarchical document tree from structured elements.

    Args:
        literature_id: ID of the literature record.
        title: Document title.
        structured_elements: List of element dicts from ODL or OCR extraction.
            Each has: type, content, page_number, heading_level (optional).

    Returns:
        A DocTree with the full hierarchy.
    """
    root = DocTreeNode(id="n0", title=title or "Document", level=0)

    if not structured_elements:
        root.content = ""
        root.element_count = 0
        return _finalize_tree(literature_id, title, root)

    # Stack tracks the path from root to the current section node.
    # Each entry: (level, node)
    stack: list[tuple[int, DocTreeNode]] = [(0, root)]
    child_counters: dict[str, int] = {"n0": 0}  # parent_id -> next child index

    # Accumulator for non-heading content destined for the current section
    content_buffer: list[str] = []
    buffer_pages: list[int] = []
    buffer_element_count = 0

    def _flush_content():
        """Flush accumulated content into a leaf node under the current parent."""
        nonlocal content_buffer, buffer_pages, buffer_element_count
        if not content_buffer:
            return

        parent_level, parent_node = stack[-1]
        text = "\n\n".join(content_buffer)

        # Split if too long
        text_chunks = _split_text(text, _MAX_LEAF_CONTENT)
        for chunk_text in text_chunks:
            leaf_id = _next_child_id(parent_node.id, child_counters)
            leaf = DocTreeNode(
                id=leaf_id,
                title=parent_node.title,
                level=parent_level + 1,
                content=chunk_text,
                page_start=min(buffer_pages) if buffer_pages else 0,
                page_end=max(buffer_pages) if buffer_pages else 0,
                element_count=buffer_element_count if len(text_chunks) == 1 else 0,
            )
            parent_node.children.append(leaf)

        content_buffer = []
        buffer_pages = []
        buffer_element_count = 0

    for el in structured_elements:
        el_type = el.get("type", "paragraph")
        content = el.get("content", "").strip()
        page = el.get("page_number", 0)
        heading_level = el.get("heading_level")

        if not content:
            continue

        if el_type == "heading":
            # Determine numeric level — use heading_level if available, else infer
            level = _resolve_heading_level(heading_level, content)

            # Flush any accumulated content before starting a new section
            _flush_content()

            # Pop stack back to find the correct parent
            while len(stack) > 1 and stack[-1][0] >= level:
                stack.pop()

            parent_level, parent_node = stack[-1]
            node_id = _next_child_id(parent_node.id, child_counters)
            section_node = DocTreeNode(
                id=node_id,
                title=content,
                level=level,
                page_start=page,
                page_end=page,
            )
            parent_node.children.append(section_node)
            child_counters[node_id] = 0
            stack.append((level, section_node))

        else:
            # Non-heading: accumulate in buffer
            content_buffer.append(content)
            buffer_pages.append(page)
            buffer_element_count += 1

    # Flush remaining content
    _flush_content()

    # Update page ranges and element counts bottom-up
    _propagate_metadata(root)

    return _finalize_tree(literature_id, title, root)


def _resolve_heading_level(heading_level: int | None, content: str) -> int:
    """Resolve heading level from metadata or heuristics."""
    if heading_level is not None and heading_level > 0:
        return heading_level

    # Heuristic: short ALL-CAPS text → level 1, otherwise level 2
    stripped = content.strip()
    if stripped.isupper() and len(stripped) < 80:
        return 1
    # Check for numbered section patterns like "1.", "1.1", "1.1.1"
    import re
    m = re.match(r"^(\d+(?:\.\d+)*)\s", stripped)
    if m:
        dots = m.group(1).count(".")
        return min(dots + 1, 4)

    return 2  # default to level 2


def _next_child_id(parent_id: str, counters: dict[str, int]) -> str:
    """Generate the next child ID under a parent."""
    idx = counters.get(parent_id, 0)
    counters[parent_id] = idx + 1
    return f"{parent_id}.{idx}"


def _split_text(text: str, max_len: int) -> list[str]:
    """Split text at paragraph boundaries to stay under max_len."""
    if len(text) <= max_len:
        return [text]

    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        if buf and len(buf) + len(para) + 2 > max_len:
            chunks.append(buf)
            buf = para
        else:
            buf = (buf + "\n\n" + para) if buf else para
    if buf:
        chunks.append(buf)

    # If any chunk still exceeds max_len, hard-split by sentences
    final: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_len:
            final.append(chunk)
        else:
            # Hard split
            while len(chunk) > max_len:
                split_at = chunk.rfind(". ", 0, max_len)
                if split_at < max_len // 2:
                    split_at = max_len
                else:
                    split_at += 1  # include the period
                final.append(chunk[:split_at].strip())
                chunk = chunk[split_at:].strip()
            if chunk:
                final.append(chunk)
    return final


def _propagate_metadata(node: DocTreeNode) -> None:
    """Recursively propagate page ranges and element counts from leaves up."""
    if node.is_leaf:
        return

    total_elements = 0
    min_page = 999999
    max_page = 0

    for child in node.children:
        _propagate_metadata(child)
        total_elements += child.element_count
        if child.page_start > 0:
            min_page = min(min_page, child.page_start)
        if child.page_end > 0:
            max_page = max(max_page, child.page_end)

    node.element_count = total_elements
    if min_page < 999999:
        node.page_start = min_page
    if max_page > 0:
        node.page_end = max_page


def _finalize_tree(literature_id: str, title: str, root: DocTreeNode) -> DocTree:
    """Create the DocTree wrapper with computed counts."""
    all_nodes = root.all_nodes()
    leaves = root.leaf_nodes()

    tree = DocTree(
        literature_id=literature_id,
        title=title,
        node_count=len(all_nodes),
        leaf_count=len(leaves),
        summaries_generated=False,
        root=root,
    )

    logger.info(
        "Doc tree built for '%s': %d nodes, %d leaves, pages %d-%d",
        title[:50],
        tree.node_count,
        tree.leaf_count,
        root.page_start,
        root.page_end,
    )
    return tree
