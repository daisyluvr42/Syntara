---
name: syntara-academic-writing
description: Use this skill when writing Chinese academic books, scholarly book chapters, professional books, or long-form academic/professional prose from PDFs, provided source documents, Syntara project libraries, PubMed records, and other available academic sources. Trigger for tasks involving WorkBuddy, Syntara MCP, RAG over literature/corpus, extracting the user's academic-book writing style, drafting chapters from a topic/title/outline, or revising book prose with citations and evidence discipline.
---

# Syntara Academic Book Writing

## Core Boundary

Use the WorkBuddy skill as the writing director. Use Syntara MCP only as the evidence and retrieval layer.

- If the task starts from ima, Tencent Docs, WorkBuddy `资料库`, or a mixed knowledge-base corpus, use `syntara-knowledge-writing` first for the source-scope, source-package, style-reference, and evidence-discipline pass, then continue here for professional-book chapter drafting.
- Skill owns: chapter planning, prose drafting, revision, evidence checks, and applying a resolved style profile.
- `syntara-style-profiler` owns: extracting and saving reusable professional-book style profiles from prior chapters or user-owned style corpus.
- Syntara MCP owns: literature search, corpus search, RAG answers, source context, citation metadata, reusable style profile extraction/storage, local PDF/PDF-folder import, PubMed search/import, and metadata enrichment from DOI/CrossRef when available.
- Do not ask Syntara MCP to write the whole chapter unless the user explicitly requests that. Keep final drafting in the WorkBuddy conversation so style and structure remain consistent.
- Do not produce a full evidence-backed chapter until Syntara evidence has been searched and checked. If Syntara retrieval is unavailable or insufficient, return an outline, a partial draft, or a `待补证据` list instead of filling gaps with general knowledge.

## Retrieval Gate

Before drafting a full chapter:

1. Confirm the Syntara project area.
2. Run at least one Syntara literature or corpus search for each major claim cluster.
3. Open context for the most important hits when a claim depends on a specific source.
4. Keep an evidence ledger with cite keys or source ids.

If `search_ready_vector: false`, do not treat Syntara as unavailable. Continue with `syntara_retrieve` using `mode: "search"`, `mode: "literature_grouped"`, and `mode: "chunk_context"`. State that vector RAG is not ready only if relevant. Do not skip retrieval and do not draft from clinical common sense alone.

If no Syntara evidence is found for a strong factual, comparative, numerical, causal, or recommendation-like claim, either soften the claim or put it under `待补证据`.

## Inputs To Collect

Before drafting, identify the available inputs:

- Topic or research question.
- Syntara project slug, such as `professional-book`, `implant-literature`, or `wechat-agent-tools`.
- Chapter title and intended section outline.
- Target reader and level of technical depth.
- Style profile or user-provided style corpus: Syntara default style profile, prior book chapters, prior sections, selected paragraphs, or WorkBuddy `资料库` / Tencent Docs material already attached in the task.
- Evidence scope: literature only, user corpus only, or both.
- Cloud source scope: whether WorkBuddy `资料库` should be used for living outlines, notes, draft material, or style examples.
- Literature import source: existing Syntara library, local PDF files/folders, user-provided source documents, PubMed PMIDs/search results, DOI/CrossRef metadata found during PDF import, or WorkBuddy `资料库` / Tencent Docs content.
- Citation style or output format if specified.

If one of topic, title, or style corpus is missing, ask a concise follow-up before producing a full chapter. For a quick exploratory draft, proceed with a clearly labeled provisional outline.

## Workflow

1. Resolve style before outlining. First check Syntara MCP for the project's default style profile. If the user supplied professional-book corpus and no suitable profile exists, use `syntara-style-profiler` to extract and save a `professional-book` Markdown + JSON profile, then apply it. For details, read `references/style-extraction.md`.

2. Choose the Syntara project area before retrieval. If the user does not name one, infer a slug from the writing task and confirm it briefly before importing durable materials. Use the same `project` value in Syntara MCP calls whenever the tool supports it.

3. Convert the topic and outline into retrieval questions. Use one question per claim cluster, not one broad query for the whole chapter.

4. Call Syntara MCP for evidence. Prefer search/context tools for source gathering, then use RAG only for bounded subquestions. If vector RAG is unavailable, continue with full-text search and chunk context. For expected tool semantics, read `references/syntara-mcp-tools.md`.

5. Use WorkBuddy `资料库` / Tencent Docs material as cloud corpus when available. Treat it as user-owned style, outline, notes, and draft context; do not treat it as peer-reviewed literature unless the document itself contains traceable citations. For details, read `references/tencent-docs-corpus.md`.

6. If the user wants to add materials to Syntara, classify them first. Import local PDFs, PDF folders, PubMed PMIDs/search results, and other formal academic source documents into the Syntara literature library when the tool supports them. Import WorkBuddy `资料库` / Tencent Docs notes, drafts, and style samples into Syntara corpus with `syntara_import` using `source_type: "corpus_text"`. Pass `project` so the material lands in the right project area. See `references/syntara-mcp-tools.md` and `references/tencent-docs-corpus.md`.

7. Create an evidence ledger before drafting. For each section, keep the claim, supporting source keys, useful quotations or paraphrases, and unresolved gaps.

8. Draft the chapter section by section. Integrate evidence naturally; do not paste RAG answers as prose. Preserve cite keys returned by Syntara, usually in `[@citekey]` form.

9. Run a final pass for citation discipline, terminology consistency, style fidelity, and unsupported claims. For detailed checks, read `references/evidence-and-citations.md`.

## Chapter Output Shape

Unless the user specifies another format, return:

- Chapter title.
- A short structural note only if helpful.
- Full chapter draft with headings matching the requested outline.
- Citation markers kept inline.
- A final "待补证据" list for claims that need more retrieval or manual confirmation.

Avoid excessive bullet points in the final prose unless the source book style clearly uses them. Professional book chapters should usually read as continuous explanatory prose with clear subheads.

## When Using Syntara MCP

Use the smallest sufficient tool call:

- Need evidence candidates: search first.
- Need surrounding passage: fetch chunk context.
- Need synthesized answer to a narrow question: use RAG.
- Need source inventory: list literature or corpus.
- Need project inventory: list projects or inspect the chosen project summary.
- Need to add formal literature: import local PDFs/PDF folders, PubMed PMIDs/search results, or other available academic source documents into Syntara literature.
- Need to add user notes/style/prose: import text into Syntara corpus.
- Need formatted bibliography: use citation/export tools if available.

If connected MCP tool names differ from the reference names, map by meaning rather than exact name.

## References

- `references/style-extraction.md`: how to infer the user's professional-book style.
- `references/syntara-mcp-tools.md`: expected Syntara MCP tool contract.
- `references/tencent-docs-corpus.md`: how to use WorkBuddy `资料库` / Tencent Docs as cloud style and draft corpus.
- `references/chapter-workflow.md`: end-to-end writing flow for a chapter.
- `references/evidence-and-citations.md`: citation and unsupported-claim checks.
- `references/skill-extension-interface.md`: how future writing-form Skills should plug into this Syntara MCP workflow.
