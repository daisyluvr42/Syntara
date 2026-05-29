---
name: syntara-knowledge-writing
description: Use this skill for general source-based writing and style-corpus reuse with Syntara, WorkBuddy, ima knowledge base, Tencent Docs, local Syntara MCP libraries, or any connected knowledge-base MCP. Trigger when the user asks to write from uploaded资料, knowledge-base documents, RAG sources, project-scoped libraries, ima资料库, Syntara文献库, Tencent Docs资料库, mixed source collections, 风格语料, 语料沉淀, style corpus, prior drafts, 往期文章, 公众号长文, or personal voice. Especially use it when the output should be a draft, article, chapter, script, brief, report, or outline with source discipline, reusable style profiles, and style control.
---

# Syntara Knowledge Writing

This is Syntara's **general source-based writing** Skill. In WorkBuddy it is displayed as `Syntara 资料写作`.

## Role

Use this Skill as the upstream writing workflow for knowledge-base materials. It does not own one specific genre. It owns the process of locating usable sources, turning them into a source package, shaping the writing task, drafting, and checking evidence/style before handoff.

This Skill is the default Syntara entrypoint for any writing task that combines source materials and style materials. If the user mentions style samples, prior writing, a corpus folder, `风格`, `语料`, `旧文`, `往期文章`, `公众号`, `style corpus`, or asks to imitate their voice, do not handle style only by reading files in the conversation. First try to create or reuse a Syntara style profile so the style can be reused later.

Use specialized Syntara Skills after this one when needed:

- `syntara-style-profiler`: extracting, updating, and saving reusable style profiles from old writings or style corpus.
- `syntara-academic-writing`: academic book chapters, professional books, and long-form scholarly writing from PDFs, provided source documents, PubMed, and other available academic sources.
- `syntara-literature-review`: literature reviews, related work, research-gap syntheses.
- Future PPT/course/social-post Skills: final format conversion after the source-backed draft is stable.

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
12. Run style pass.
13. Run evidence pass.

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
6. **Style pass**: align to the resolved style mode and remove generic AI phrasing.
7. **Evidence pass**: check source support, unsupported claims, data, citations, and manual verification points.

## Style Handling

Style is mandatory, not optional. Before drafting, choose exactly one style mode and keep it visible in the working plan:

- **User voice**: use when a Syntara style profile, prior drafts, representative paragraphs, a style corpus, or a named user-writing collection is available.
- **Named style**: use when the prompt names an author, publication, genre, or style target.
- **Source-document style**: use only when the user asks to imitate the style of the provided sources; otherwise sources are evidence, not style.
- **Default de-AI**: use when no style reference is provided.

For formal writing tasks such as articles, chapters, reports, review drafts, scripts, or deck narratives, proactively check Syntara MCP for a style profile before outlining:

1. Infer the Syntara `project` from the task or use the project named by the user.
2. Infer the `style_type` from the requested output, such as `wechat-longform`, `professional-book`, `literature-review`, `tutorial`, `report`, `script`, or `ppt`.
3. Call `syntara_list_style_profiles` with the inferred `project` and `style_type` when available; then call `syntara_get_style_profile` for the best matching profile. In WorkBuddy, these custom MCP tools may appear as `syntara_syntara_list_style_profiles` and `syntara_syntara_get_style_profile`; use the visible tool with the same meaning.
4. If no type-specific match exists, call `syntara_get_style_profile` with `default: true` for that project when available.
5. If the project default is not found or the project is unclear, call `syntara_list_style_profiles` with no project filter.
6. If `syntara_list_style_profiles` returns exactly one profile, or one clear default profile, call `syntara_get_style_profile` for that profile id and use its `profile_markdown` as the style brief.
7. If no profile exists, run first-use style setup before defaulting:
   - Look for user-owned style samples in the prompt, attached files, current WorkBuddy/ima/Tencent Docs knowledge base, or Syntara corpus. Likely titles/tags include `style-corpus`, `style`, `风格`, `旧文`, `往期文章`, `代表作`, `书稿`, `章节`, `公众号`, `草稿`, or `voice`.
   - If mixed style samples from different genres or writing types are found, group them by `style_type` first. Build separate profiles instead of merging them.
   - If style samples are found and readable, use `syntara-style-profiler` to extract a normalized Markdown + JSON style profile and save it with Syntara MCP. This keeps style extraction separate from drafting.
   - If several possible style sources are found, ask the user to choose the intended one before building the default profile.
   - If no style source is found, say briefly that no personal style corpus is configured yet, and offer the shortest setup path: “send/attach 2-5 representative drafts or point me to a knowledge-base folder.” Do not block the task unless the user explicitly asked for their own voice.
8. If the user provides style corpus, prior drafts, or asks to build a voice, route the extraction through `syntara-style-profiler` before drafting. Do this even when the corpus has already been read directly, because reading is not the same as durable style setup.
9. If no profile or corpus is available and the user wants to continue, use `default_de_ai` and label it as not the user's personal voice.

For formal writing, do not start drafting until the style mode is resolved. If a Syntara profile is available, `profile_markdown` must be read and applied during both outline and final style pass; listing the profile is not enough. If this is the user's first Syntara writing task and no profile exists, the first-use style setup above is part of resolving style mode.

Do not interrupt lightweight tasks such as summaries, extraction, translation, or source inventory just to ask about style.

If the user provides style corpus or names a style source, use the style profile before outlining. If no structured profile exists yet, extract or build one first. Capture:

- sentence rhythm and paragraph length;
- how claims are introduced;
- whether the style prefers narrative, operational steps, or argument;
- treatment of examples, numbers, and caveats;
- terms and phrases to preserve or avoid.

Do not merge unlike style corpora. A user's professional book chapters, public essays, tutorials, social posts, and slide scripts should become separate style profiles unless the user explicitly asks for a combined house style.

If the prompt does not specify a style reference and no Syntara style profile is found, do not claim to be writing in the user's own style. Continue with the default de-AI pass unless the user asked to wait.

Default de-AI pass:

- remove empty slogans and generic AI phrasing;
- reduce over-neat numbered frameworks unless the genre needs them;
- replace abstract claims with concrete mechanisms or examples;
- avoid invented audience thoughts and fake statistics;
- keep uncertainty and source boundaries visible.

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
