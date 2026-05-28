"""RAG (Retrieval-Augmented Generation) service.

Supports two modes:
1. Standard RAG: vector+FTS hybrid search → context → LLM
2. Hybrid RAG (tree-enhanced): vector+FTS finds top docs, then PageIndex-style
   tree navigation drills into each doc for precise leaf-level context.
"""

from __future__ import annotations

import logging

from backend.services.ai_provider import chat_completion
from backend.services.searcher import hybrid_search

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a research assistant helping with academic writing.
Answer the user's question based ONLY on the provided literature excerpts.
For each claim, cite the source using the format [@citekey].
If the excerpts don't contain enough information, say so honestly.
Respond in the same language as the user's question."""


async def rag_query(
    question: str,
    provider_id: str | None = None,
    search_scope: str = "all",
    top_k: int = 5,
    use_tree: bool = True,
    project: str | None = None,
) -> dict:
    """
    Hybrid RAG pipeline:
    1. Search for relevant passages (vector + FTS)
    2. If tree navigation is enabled, enhance top results with precise tree context
    3. Build prompt with context
    4. Call LLM
    5. Return answer with citations
    """
    # Step 1: Retrieve relevant passages
    results = await hybrid_search(question, scope=search_scope, top_k=top_k, project=project)

    # Step 2: Enhance with tree navigation (Layer 2)
    if use_tree and results:
        results = await _enhance_with_tree_navigation(question, results, provider_id)

    # Step 3: Build context with structured metadata
    context_parts = []
    cited_keys = []
    for r in results:
        cite_key = r.get("cite_key", "")
        title = r.get("title", "")
        snippet = r.get("snippet", r.get("abstract", ""))
        heading = r.get("heading", "")
        page_number = r.get("page_number", 0)
        element_type = r.get("element_type", "paragraph")
        tree_path = r.get("tree_path", "")

        if snippet:
            source_label = f"[@{cite_key}]" if cite_key else f"[{title}]"
            location_parts = []
            if tree_path:
                location_parts.append(f"Path: {tree_path}")
            elif heading:
                location_parts.append(f"Section: {heading}")
            if page_number:
                location_parts.append(f"p.{page_number}")
            if element_type and element_type != "paragraph":
                location_parts.append(f"type: {element_type}")
            location = f" ({', '.join(location_parts)})" if location_parts else ""
            context_parts.append(f"--- Source: {source_label} ({title}){location} ---\n{snippet}")
            if cite_key:
                cited_keys.append(cite_key)

    context_text = "\n\n".join(context_parts) if context_parts else "No relevant passages found."

    # Step 4: Build messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"## Relevant literature excerpts:\n\n{context_text}\n\n## Question:\n{question}",
        },
    ]

    # Step 5: Call LLM
    try:
        answer = await chat_completion(provider_id, messages)
    except Exception as e:
        answer = f"AI service error: {str(e)}"

    return {
        "answer": answer,
        "sources": results,
        "cited_keys": cited_keys,
    }


async def _enhance_with_tree_navigation(
    query: str,
    results: list[dict],
    provider_id: str | None,
) -> list[dict]:
    """Enhance search results with precise context from document trees.

    For each literature result that has a document tree, run the tree navigator
    to find the most relevant leaf nodes. Replace the generic vector-search
    snippet with the precise leaf content.
    """
    from backend.services.doc_tree_cache import load_tree
    from backend.services.doc_tree_navigator import navigate_tree

    enhanced = []
    tree_hits = 0

    for r in results:
        # Only enhance literature results (not corpus)
        if r.get("source_type") != "literature":
            enhanced.append(r)
            continue

        lit_id = r.get("id", "")
        tree = load_tree(lit_id)

        if not tree or not tree.summaries_generated:
            # No tree or unsummarized — keep original result
            enhanced.append(r)
            continue

        # Navigate the tree for precise context
        try:
            leaves = await navigate_tree(tree, query, beam_width=2, provider_id=provider_id)
            if leaves:
                tree_hits += 1
                for leaf in leaves:
                    # Build tree path: trace from root
                    tree_path = _build_tree_path(tree.root, leaf.id)
                    enhanced.append({
                        **r,
                        "snippet": leaf.content,
                        "heading": leaf.title,
                        "page_number": leaf.page_start,
                        "element_type": "tree_leaf",
                        "tree_path": tree_path,
                    })
            else:
                # Navigation found nothing — keep original
                enhanced.append(r)
        except Exception as e:
            logger.warning("Tree navigation failed for %s: %s", lit_id[:12], e)
            enhanced.append(r)

    if tree_hits > 0:
        logger.info("Tree navigation enhanced %d/%d results", tree_hits, len(results))

    return enhanced


def _build_tree_path(root, target_id: str) -> str:
    """Build a breadcrumb path from root to the target node."""
    path_parts: list[str] = []

    def _find(node, target: str) -> bool:
        if node.id == target:
            path_parts.append(node.title)
            return True
        for child in node.children:
            if _find(child, target):
                path_parts.append(node.title)
                return True
        return False

    _find(root, target_id)
    path_parts.reverse()
    # Skip root title (document title) — start from first section
    if len(path_parts) > 1:
        return " > ".join(path_parts[1:])
    return path_parts[0] if path_parts else ""


async def ai_action(
    action: str,
    text: str,
    provider_id: str | None = None,
    source_lang: str = "en",
    target_lang: str = "zh",
) -> str:
    """
    Perform an AI action on text:
    - summarize: Generate a structured summary
    - translate: Translate between languages
    - rewrite: Academic-style rewriting/polishing
    - expand: Expand outline into full paragraph
    - explain_term: Explain a technical term
    - logic_check: Revise text for logical consistency
    - deai: Make wording sound more natural
    - research_gap: Identify open questions and future directions
    - paper_structure: Suggest a paper outline or restructuring
    - citation_check: Mark claims that need citations
    - abstract_draft: Draft a structured abstract
    """
    prompts = {
        "summarize": f"Provide a concise, structured summary of the following academic text. Use bullet points for key findings:\n\n{text}",
        "translate": f"Translate the following text from {source_lang} to {target_lang}. Preserve academic terminology accurately:\n\n{text}",
        "rewrite": f"Rewrite the following text in formal academic style. Improve clarity and flow while preserving the original meaning:\n\n{text}",
        "expand": f"Expand the following outline/notes into a well-written academic paragraph with proper transitions:\n\n{text}",
        "explain_term": f"Explain the following term/concept in the context of academic research. Provide a clear definition and relevant context:\n\n{text}",
        "logic_check": f"Revise the following academic text for logical consistency. Fix weak causal links, contradictions, unsupported jumps in reasoning, and unclear argument flow. If a claim is not adequately supported, soften it rather than inventing evidence. Return only the revised text:\n\n{text}",
        "deai": f"Rewrite the following text so it sounds more natural and human while remaining academically credible. Remove formulaic or overly generic AI-style phrasing, but preserve the original meaning and technical accuracy. Return only the revised text:\n\n{text}",
        "research_gap": f"Analyze the following text and identify the main research gaps, underexplored directions, and promising next-step questions. Present the result in short labeled sections:\n\n{text}",
        "paper_structure": f"Analyze the following text and propose a clearer academic paper structure. Return a concise section-by-section outline with brief notes on what each section should cover:\n\n{text}",
        "citation_check": f"Review the following text and mark statements that likely need citations but do not appear to be supported. Add [citation needed] inline where appropriate, preserve any existing citations, and return only the annotated text:\n\n{text}",
        "abstract_draft": f"Draft a structured academic abstract from the following text. Use the headings Background, Methods, Results, and Conclusion:\n\n{text}",
    }

    user_prompt = prompts.get(action)
    if not user_prompt:
        raise ValueError(f"Unknown action: {action}")

    messages = [
        {"role": "system", "content": "You are a helpful academic writing assistant. Respond in the same language as the input unless translating."},
        {"role": "user", "content": user_prompt},
    ]

    return await chat_completion(provider_id, messages)
