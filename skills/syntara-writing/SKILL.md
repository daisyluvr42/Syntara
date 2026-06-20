---
name: syntara-writing
description: Use this skill for Syntara writing from sources and reusable style profiles. Trigger for articles, chapters, academic/professional book prose, literature reviews, related-work sections, research-gap syntheses, reports, briefs, scripts, outlines, de-AI passes, and drafts from uploaded资料, knowledge-base documents, RAG sources, Syntara project libraries, PubMed records, ima资料库, Tencent Docs, WorkBuddy资料库, 风格语料, prior drafts, 往期文章, 公众号长文, or personal voice.
---

# Syntara Writing

This is Syntara's unified **source-based writing** Skill. In WorkBuddy it is displayed as `Syntara 写作`.

## Role

Use this Skill as the upstream writing workflow for knowledge-base materials. It does not own one specific genre. It owns the process of locating usable sources, turning them into a source package, shaping the writing task, drafting, and checking evidence/style before handoff.

This Skill is the default Syntara entrypoint for any writing task that combines source materials and style materials. If the user mentions style samples, prior writing, a corpus folder, `风格`, `语料`, `旧文`, `往期文章`, `公众号`, `style corpus`, or asks to imitate their voice, do not handle style only by reading files in the conversation. First try to create or reuse a Syntara style profile so the style can be reused later.

Use one separate Syntara Skill when needed:

- `syntara-style-profiler`: extracting, updating, and saving reusable style profiles from old writings or style corpus.

Academic book chapters, professional prose, literature reviews, related-work sections, research-gap syntheses, reports, scripts, and public articles are handled inside this Skill as different writing modes, not as separate user-visible Skills.

## Fixed Workflow

Follow this order unless the user explicitly requests a shorter path.

1. Confirm knowledge-base availability.
2. Browse relevant available MCPs and connectors.
3. Respect any source location or scope named in the prompt.
4. Find files.
5. Find themes.
6. Build the source package.
7. Resolve style mode and persist reusable style when possible.
8. Confirm topic scope.
9. Draft structure.
10. Draft outline.
11. Write the body.
12. Run style-aware review.
13. Write a revision plan.
14. Revise the draft.
15. Run final style and evidence gates.
16. Learn only after human review.

If the user asks for direct writing, compress steps 6-9 into a short internal pass, but still do them.

## Knowledge-Base Availability

Start by checking which source systems are available and relevant:

- WorkBuddy `资料库` / ima knowledge base.
- Syntara MCP project libraries.
- Tencent Docs or other cloud document connectors.
- Local files only if the prompt allows them.
- Any other connected MCP that can list, search, or fetch source content.

If the prompt names a knowledge base, folder, project, tag, or document list, stay inside that scope. If the prompt says not to read local files, do not use local files. If the prompt does not name a scope, infer the most likely knowledge base from the task and state the assumed scope briefly before making durable imports or broad searches.

For ima specifically, do not treat a first empty list as final. Retry by browsing personal/shared knowledge-base types if the tool supports it. New uploads may need parsing time, and scanned PDFs may need longer OCR time.

## Source Reading Law

Default to using background material only inside the selected knowledge-base scope unless the user allows broader search.

Use this retrieval order:

1. **Find files**: list or search document inventory by title, collection, tag, project, or file type.
2. **Find themes**: search core terms, synonyms, named frameworks, data points, and expected controversies.
3. **Fetch key content**: open or fetch the most important files before using them as evidence.
4. **Separate evidence from context**: source text supports factual claims; general background only informs framing.

Do not treat a file title, snippet, intro, or summary as full-text evidence. If only metadata or preview text is available, say so.

For detailed source and style rules, read `references/source-style-evidence.md` when the task involves factual claims, citations, style adaptation, or publication-quality output.

For expected MCP tool usage, read `references/syntara-mcp-tools.md`.

## Writing Flow

Convert the user's prompt into a writing brief:

- Target output: article, chapter, report, script, outline, post, deck narrative, or other.
- Reader: expert, practitioner, beginner, public audience, buyer, student, etc.
- Scope: what is included and excluded.
- Source base: which knowledge base, project, files, or tags.
- Style mode: user-supplied corpus, named author/style, prior drafts, source-document style, or default de-AI pass.
- Required evidence behavior: citations, file names, page numbers, quote snippets, or manual-check list.

Then proceed:

1. **Source package**: summarize usable sources by role, not by upload order.
2. **Style mode**: decide the prose target before drafting.
3. **Structure**: propose the argument path or section sequence.
4. **Outline**: make section-level claims and evidence needs explicit.
5. **Body draft**: write naturally for the target genre; do not paste RAG answers.
6. **Style-aware review memo**: review the draft before revising. The review must use the resolved style profile and any selected exemplars.
7. **Revision plan**: decide what to change and what to preserve. Do not rewrite directly from the review memo.
8. **Revised draft**: revise only according to the plan.
9. **Final gates**: run style, evidence, and human-revision checks.
10. **Learning gate**: update the style profile only from user feedback, user comments, or a user-edited/final version.

## Specialized Writing Modes

Use the same top-level workflow, then apply the branch that matches the requested output.

### Academic Or Professional Chapters

- Confirm topic, project, chapter title or outline, target reader, evidence scope, citation needs, and style profile.
- Before drafting a full chapter, run Syntara literature or corpus retrieval for each major claim cluster.
- Use `syntara_retrieve` with `mode: "search"`, `mode: "literature_grouped"`, and `mode: "chunk_context"` for evidence. Use `mode: "rag_answer"` only for bounded subquestions.
- Keep an evidence ledger with claim, source id or cite key, useful passage, and unresolved gap.
- Draft section by section. Preserve cite keys such as `[@citekey]` when returned.
- If evidence is insufficient for a strong factual, comparative, numerical, causal, or recommendation-like claim, soften the claim or list it under `待补证据`.

### Literature Reviews And Related Work

- Confirm review type, topic or review question, project, audience, inclusion boundaries, output shape, citation style, and language.
- Build search strands before drafting: core concept, synonyms, mechanism, application setting, methods, controversies, and recent advances.
- Build a synthesis matrix with source, population or domain, method, finding, limitation, and effect on the review argument.
- Draft by synthesis, not by paper order. Organize around mechanisms, themes, disagreements, evidence strength, and gaps.
- Do not produce a full review until Syntara evidence has been searched and the synthesis matrix has source-backed entries. If retrieval is insufficient, return a search report and `待补证据`.

### Public Articles, Reports, Scripts, And Briefs

- Use the same source package and style profile workflow.
- Match `style_type` to the public taxonomy: `article`, `blog-article`, `op-ed`, `business-report`, `technical-report`, `white-paper`, `proposal`, `memo-email`, `presentation`, `talk-script`, `course-script`, `social-post`, or `general`.
- Keep evidence lighter or heavier according to the genre, but never invent source labels, statistics, page numbers, or quotes.

## Style Handling

Style is mandatory, not optional. Before drafting, choose exactly one style mode and keep it visible in the working plan:

- **User voice**: use when a Syntara style profile, prior drafts, representative paragraphs, a style corpus, or a named user-writing collection is available.
- **Named style**: use when the prompt names an author, publication, genre, or style target.
- **Source-document style**: use only when the user asks to imitate the style of the provided sources; otherwise sources are evidence, not style.
- **Default de-AI**: use when no style reference is provided.

For formal writing tasks such as articles, chapters, reports, review drafts, scripts, or deck narratives, proactively check Syntara MCP for a style profile before outlining:

1. Infer the Syntara `project` from the task or use the project named by the user.
2. Infer `writing_mode` and `style_type` from the requested output. Use common public values rather than user-specific topics. Common `writing_mode` values are `argument`, `informative-explanatory`, `narrative`, `descriptive`, and `mixed`. Common `style_type` values include `academic-paper`, `abstract`, `literature-review`, `research-proposal`, `review-critique`, `technical-report`, `business-report`, `white-paper`, `proposal`, `memo-email`, `business-letter`, `documentation`, `instructional-guide`, `manual`, `article`, `blog-article`, `op-ed`, `review`, `newsletter`, `social-post`, `presentation`, `talk-script`, `course-script`, `personal-statement`, `reflection`, `creative-nonfiction`, `narrative`, and `general`.
3. Call `syntara_style_profile` with `action: "list"`, the inferred `project`, and `style_type` when available; then call `syntara_style_profile` with `action: "get"` for the best matching profile.
4. If no type-specific match exists, call `syntara_style_profile` with `action: "get"` and `default: true` for that project when available.
5. If the project default is not found or the project is unclear, call `syntara_style_profile` with `action: "list"` and no project filter.
6. If the list returns exactly one profile, or one clear default profile, call `syntara_style_profile` with `action: "get"` for that profile id and use its `profile_markdown` as the style brief. Also inspect `profile_json.style_exemplars` when present.
7. If no profile exists, run first-use style setup before defaulting:
   - Look for user-owned style samples in the prompt, attached files, current WorkBuddy/ima/Tencent Docs knowledge base, or Syntara corpus. Likely titles/tags include `style-corpus`, `style`, `风格`, `旧文`, `往期文章`, `代表作`, `书稿`, `章节`, `公众号`, `草稿`, or `voice`.
   - If mixed style samples from different genres or writing types are found, group them by common `style_type` first. Build separate profiles instead of merging them.
   - If style samples are found and readable, use `syntara-style-profiler` to extract a normalized Markdown + JSON style profile and save it with Syntara MCP. This keeps style extraction separate from drafting.
   - If several possible style sources are found, ask the user to choose the intended one before building the default profile.
   - If no style source is found, say briefly that no personal style corpus is configured yet, and offer the shortest setup path: “send/attach 2-5 representative drafts or point me to a knowledge-base folder.” Do not block the task unless the user explicitly asked for their own voice.
8. If the user provides style corpus, prior drafts, or asks to build a voice, route the extraction through `syntara-style-profiler` before drafting. Do this even when the corpus has already been read directly, because reading is not the same as durable style setup.
9. If no profile or corpus is available and the user wants to continue, use `default_de_ai` and label it as not the user's personal voice.

For formal writing, do not start drafting until the style mode is resolved. If a Syntara profile is available, `profile_markdown` must be read and applied during both outline and final style pass; listing the profile is not enough. If `profile_json.style_exemplars` is available, select 2-4 exemplars that match the current task before outlining. If this is the user's first Syntara writing task and no profile exists, the first-use style setup above is part of resolving style mode.

When using style exemplars:

- Match by task and passage role: `opening` for leads, `judgment` for thesis paragraphs, `mechanism` for explanation, `counterargument` for correction, `tutorial` for step-by-step material, `investment` for valuation/market writing, `product-note` for release notes, `ending` for close, and `revision-gold` for the strongest user-edited voice.
- Put only the selected short excerpts into the working context. Do not load the whole style corpus just because exemplars exist.
- Imitate rhythm, judgment flow, paragraph breath, and explanation order. Do not copy the factual content or reuse phrasing unless the user explicitly asks to reuse their own text.
- If no exemplar matches the task, rely on the profile rules and state no style exemplar matched.

Do not interrupt lightweight tasks such as summaries, extraction, translation, or source inventory just to ask about style.

If the user provides style corpus or names a style source, use the style profile before outlining. If no structured profile exists yet, extract or build one first. Capture:

- sentence rhythm and paragraph length;
- how claims are introduced;
- whether the style prefers narrative, operational steps, or argument;
- treatment of examples, numbers, and caveats;
- terms and phrases to preserve or avoid.

Do not merge unlike style corpora. A user's professional book chapters, public essays, tutorials, social posts, and slide scripts should become separate style profiles unless the user explicitly asks for a combined house style.

Use the generic public `style_type` values from `syntara-style-profiler/references/style-taxonomy.md` for new profiles. Put platform, topic, or user-specific distinctions in tags, `genre_matrix`, or `style_exemplars.category`.

If the prompt does not specify a style reference and no Syntara style profile is found, do not claim to be writing in the user's own style. Continue with the default de-AI pass unless the user asked to wait.

## Review And Revise Loop

For publication-quality drafts, the first draft is not final. Run this loop:

1. Produce the draft from the source package, style package, and argument plan.
2. Call `syntara_style_profile` with `action: "prepare_review"` before revising.
3. Use the returned style package, profile rules, selected exemplars, anti-AI rules, and revision preferences to write a review memo.
4. Write a revision plan from the review memo.
5. Revise the draft according to the plan.
6. Run the final style and evidence gates.
7. Ask for, wait for, or accept human review before learning.

The review memo must check:

- argument: whether the central judgment is clear and whether the text only stacks material;
- evidence: whether strong factual, numerical, causal, or quoted claims are supported;
- structure: whether the draft copies the input outline instead of building a real argument path;
- style: whether it follows the style profile and exemplars in judgment rhythm, paragraph breath, and explanation order, not just formatting;
- AI patterns: generic transitions, inflated era claims, decorative contrast, slogan endings, or over-neat numbered frameworks;
- preservation: what should stay rough, direct, or uneven because it carries the author's hand.

Do not learn from AI-only material. Never update a style profile from Syntara's own review memo, revision plan, or second draft. Learning may happen only after the user provides feedback, comments, a revised passage, or a final version. Use `syntara_style_profile` with `action: "learn_from_human_review"` for that step.

Default de-AI pass:

- remove empty slogans and generic AI phrasing;
- reduce over-neat numbered frameworks unless the genre needs them;
- replace abstract claims with concrete mechanisms or examples;
- avoid invented audience thoughts and fake statistics;
- keep uncertainty and source boundaries visible.

## Human Revision Gate

When polishing, revising, rewriting, or de-AI-ing user-owned prose, read `references/human-revision-gate.md` before the final style pass.

Use it especially when the user says the AI version lost taste, voice, personality, or `人味儿`.

Rules for this pass:

- Change less than feels tempting. If a sentence is merely rough but still carries the author's position, rhythm, or hesitation, keep it.
- Treat colloquial particles, uneven paragraph breath, plain observations, and odd but intentional phrasing as possible author hand, not defects.
- Check only the sentences Syntara changed or added. Do not scan untouched user prose as if it were AI output.
- Avoid replacing the user's plain observation with a prettier metaphor, slogan, balanced contrast, or three-part structure.
- For sensitive polish tasks, keep a short internal ledger of what changed, why, and whether it can be reverted.

## Evidence Discipline

Never invent page numbers, source titles, authors, statistics, or quote locations. If page numbers are unavailable, cite file names only. If a key claim depends on a table, figure, clinical number, legal rule, financial figure, or exact quote, list it under manual verification.

Use source labels close to the claim when the output is research/professional writing. For public-facing prose, source labels may be lighter, but the final evidence note should still list the main files used and unresolved checks.

## Output Shape

Unless the user asks for a specific format, return:

1. Title or working title.
2. Final draft or requested writing artifact.
3. Main sources used.
4. Manual verification points.
5. Optional next-step note if the draft needs style corpus, page checks, or source expansion.

For long tasks, produce the source package and outline first if the prompt asks for planning. If the prompt asks for a finished draft, include only a brief evidence note at the end.
