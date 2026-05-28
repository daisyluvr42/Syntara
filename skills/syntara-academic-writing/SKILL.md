---
name: syntara-academic-writing
description: Use this skill when writing Chinese professional or academic book chapters with Syntara as the evidence library. Trigger for tasks involving WorkBuddy, Syntara MCP, RAG over literature/corpus, extracting the user's professional-book writing style, drafting chapters from a topic/title/outline, or revising chapter prose with citations and evidence discipline.
---

# Syntara Academic Writing

## Core Boundary

Use the WorkBuddy skill as the writing director. Use Syntara MCP only as the evidence and retrieval layer.

- Skill owns: style extraction, chapter planning, prose drafting, revision, evidence checks.
- Syntara MCP owns: literature search, corpus search, RAG answers, source context, citation metadata.
- Do not ask Syntara MCP to write the whole chapter unless the user explicitly requests that. Keep final drafting in the WorkBuddy conversation so style and structure remain consistent.

## Inputs To Collect

Before drafting, identify the available inputs:

- Topic or research question.
- Syntara project slug, such as `professional-book`, `implant-literature`, or `wechat-agent-tools`.
- Chapter title and intended section outline.
- Target reader and level of technical depth.
- User-provided style corpus: prior book chapters, prior sections, selected paragraphs, or WorkBuddy `资料库` / Tencent Docs material already attached in the task.
- Evidence scope: literature only, user corpus only, or both.
- Cloud source scope: whether WorkBuddy `资料库` should be used for living outlines, notes, draft material, or style examples.
- Literature import source: existing Syntara library, local PDF files/folders, PubMed PMIDs, or WorkBuddy `资料库` / Tencent Docs content.
- Citation style or output format if specified.

If one of topic, title, or style corpus is missing, ask a concise follow-up before producing a full chapter. For a quick exploratory draft, proceed with a clearly labeled provisional outline.

## Workflow

1. Build a style brief from the user's supplied professional-book corpus. Capture paragraph rhythm, explanation order, terminology habits, use of examples, claim strength, and how experience-based judgment is separated from literature-backed claims. For details, read `references/style-extraction.md`.

2. Choose the Syntara project area before retrieval. If the user does not name one, infer a slug from the writing task and confirm it briefly before importing durable materials. Use the same `project` value in Syntara MCP calls whenever the tool supports it.

3. Convert the topic and outline into retrieval questions. Use one question per claim cluster, not one broad query for the whole chapter.

4. Call Syntara MCP for evidence. Prefer search/context tools for source gathering, then use RAG only for bounded subquestions. For expected tool semantics, read `references/syntara-mcp-tools.md`.

5. Use WorkBuddy `资料库` / Tencent Docs material as cloud corpus when available. Treat it as user-owned style, outline, notes, and draft context; do not treat it as peer-reviewed literature unless the document itself contains traceable citations. For details, read `references/tencent-docs-corpus.md`.

6. If the user wants to add materials to Syntara, classify them first. Import local PDFs or PubMed PMIDs into the Syntara literature library. Import WorkBuddy `资料库` / Tencent Docs notes, drafts, and style samples into Syntara corpus with `syntara_import_corpus_text`. Pass `project` so the material lands in the right project area. See `references/syntara-mcp-tools.md` and `references/tencent-docs-corpus.md`.

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
- Need to add formal literature: import local PDFs or PubMed PMIDs into Syntara literature.
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
