---
name: syntara-literature-review
description: Use this skill when writing Chinese or bilingual literature reviews, narrative reviews, scoping-review style drafts, related-work sections, research-gap summaries, or evidence syntheses with Syntara MCP project-scoped RAG and citations.
---

# Syntara Literature Review

## Boundary

Use WorkBuddy as the writing surface, this Skill as the review-writing director, and Syntara MCP as the project-scoped evidence library.

- Skill owns: review question framing, inclusion logic, theme synthesis, controversy mapping, research-gap analysis, prose drafting, citation checks.
- Syntara MCP owns: project areas, literature search, RAG, source context, imports, citation metadata, BibTeX export.
- Do not let RAG write the whole review. Use RAG to answer bounded evidence questions, then synthesize in the WorkBuddy conversation.

## Inputs To Collect

- Review type: narrative review, scoping-style review, related-work section, grant/background review, or book-chapter literature review.
- Topic or review question.
- Syntara project slug.
- Target audience and publication/use context.
- Evidence scope: existing project library, new PubMed search, local PDFs, Tencent Docs notes, or mixed sources.
- Inclusion boundaries: dates, population/domain, intervention/technology, methods, languages, source types.
- Output shape: thematic review, chronological review, mechanism-based review, controversy/gap review, or IMRaD-like structure.
- Citation style and language.

If topic, review type, or project slug is missing, ask one concise follow-up before writing the full review. For a quick exploratory map, proceed with a provisional project slug and label it provisional.

## Workflow

1. Select the project. Use `syntara_list_projects` or `syntara_project_summary` when the project is unclear.

2. Frame the review question and boundaries. Convert the topic into inclusion/exclusion criteria, even if informal. For details, read `references/review-workflow.md`.

3. Build search strands. Use several targeted queries: core concept, synonyms, mechanism, clinical/application setting, methods, controversies, and recent advances.

4. Retrieve evidence with Syntara MCP using the chosen `project`. Prefer `syntara_search_literature_grouped` for source discovery, `syntara_get_chunk_context` for support checks, and `syntara_rag_answer` only for bounded subquestions.

5. Build a synthesis matrix before drafting. Track source, population/domain, method, finding, limitation, and how it affects the review argument. For details, read `references/synthesis-matrix.md`.

6. Draft by synthesis, not by paper order. Organize around mechanisms, themes, disagreements, evidence strength, and unresolved gaps.

7. Run a final evidence pass. Check that each strong claim has a source, each citation supports the sentence it follows, and uncertainty is stated honestly.

## Output Shape

Unless the user specifies another format, return:

- Review title.
- Scope note: one short paragraph on what is included and excluded.
- Main review with clear thematic headings.
- Evidence-gap section.
- Optional table-like synthesis matrix if useful.
- Inline citation markers in `[@citekey]` form.
- `待补证据` list for claims needing more retrieval.

## When To Use Other Syntara Skills

- Use `syntara-academic-writing` when the target is a professional book chapter with literature support.
- Use this Skill when the target is primarily a literature synthesis, related-work section, or research-gap review.
- Future writing-form Skills should follow `references/skill-extension-interface.md`.

## References

- `references/review-workflow.md`: review framing and retrieval flow.
- `references/synthesis-matrix.md`: synthesis matrix and evidence-strength checks.
- `references/syntara-mcp-tools.md`: MCP tools most relevant to literature reviews.
- `references/skill-extension-interface.md`: how future writing-form Skills plug into Syntara MCP.
