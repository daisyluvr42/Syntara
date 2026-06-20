# Source, Style, And Evidence Rules

## Knowledge-Base Checks

Before writing from a knowledge base, confirm three things:

1. The target knowledge base, project, tag, folder, or file group is visible.
2. The needed files are parsed or otherwise fetchable.
3. The connector can provide enough content for the requested task.

For ima, remember these observed behaviors:

- `get_knowledge_base_list` may return empty when called without the right knowledge-base type. Retry personal and shared scopes when available.
- A newly uploaded file can appear in the UI before its text is searchable.
- Scanned PDFs can take longer to parse and OCR.
- `fetch_media_content` may provide OCR/text content but not stable original PDF page numbers.

## Source Package

Build the source package around source roles:

- **Core source**: directly supports the main thesis or primary factual content.
- **Framework source**: provides structure, terminology, workflow, or method.
- **Evidence source**: provides data, cases, quotes, figures, or comparison points.
- **Style source**: provides prose rhythm, tone, or user voice.
- **Background source**: helps orientation but should not carry precise claims.

Do not summarize every file mechanically. Select sources according to the user's goal.

## Claim Strength

Classify claims before drafting:

- **Strong factual claim**: needs direct source support.
- **Numerical claim**: needs exact source and manual check if page/table unavailable.
- **Causal claim**: needs source support or softened language.
- **Operational recommendation**: needs either source support or clear labeling as practical synthesis.
- **Interpretive claim**: can be written as analysis, but should not pretend to be source fact.

If support is weak, soften the sentence or move it to `待补证据` / manual verification.

## Style Defaults

Treat style as a separate decision from evidence. A document can be used as factual source without being used as style source.

For formal writing, check Syntara style profiles before defaulting:

1. Infer `writing_mode` and `style_type` from the requested output. Use common public taxonomy:
   - `writing_mode`: `argument`, `informative-explanatory`, `narrative`, `descriptive`, or `mixed`.
   - `style_type`: `academic-paper`, `abstract`, `literature-review`, `research-proposal`, `review-critique`, `technical-report`, `business-report`, `white-paper`, `proposal`, `memo-email`, `business-letter`, `documentation`, `instructional-guide`, `manual`, `article`, `blog-article`, `op-ed`, `review`, `newsletter`, `social-post`, `presentation`, `talk-script`, `course-script`, `personal-statement`, `reflection`, `creative-nonfiction`, `narrative`, or `general`.
2. Use `syntara_style_profile` with `action: "list"`, the inferred project, and `style_type` when available.
3. If no type-specific profile is found, use `syntara_style_profile` with `action: "get"` and `default: true` for the inferred project.
4. If not found, use `syntara_style_profile` with `action: "list"` without a project filter and choose a clear single/default match.
5. After choosing a listed profile, call `syntara_style_profile` with `action: "get"` for its id. Do not draft from the list summary alone.
   - Read `profile_markdown` as the rule brief.
   - If `profile_json.style_exemplars` exists, choose 2-4 short exemplars that match the current task or passage role.
6. If no profile exists, run first-use style setup:
   - Search the available user-owned corpus or connected knowledge base for likely style samples: `style-corpus`, `style`, `风格`, `旧文`, `往期文章`, `代表作`, `书稿`, `章节`, `公众号`, `草稿`, `voice`.
   - If the style corpus contains different genres or writing types, group by style type and build separate profiles.
   - If exactly one obvious style source is found, use `syntara-style-profiler` to extract and save a Markdown + JSON project default profile with the inferred `style_type`.
   - If multiple candidates are found, ask the user to choose.
   - If none are found, continue only with `default_de_ai` unless the user asked for their own voice, in which case ask for 2-5 representative drafts or a folder/document location.
7. If the task includes style corpus, route style extraction through `syntara-style-profiler`; it should save a normalized profile with `syntara_style_profile` using `action: "build"` or `action: "save"`.
8. If no profile exists and the user wants to continue, keep writing with `default_de_ai` and state that this is not the user's personal voice.

Before drafting, choose one style mode:

- `user_voice`: when a Syntara style profile, prior drafts, representative paragraphs, or an explicit user-style corpus are available.
- `named_style`: when the prompt names a publication, author, genre, or house style.
- `source_document_style`: only when the user explicitly asks to imitate the uploaded sources' prose.
- `default_de_ai`: when no style source is specified.

Do not silently skip style. If no style reference or Syntara profile is available, use `default_de_ai` rather than the user's personal voice.

Use the generic public `style_type` values from `syntara-style-profiler/references/style-taxonomy.md` for new profiles. Put platform, topic, or user-specific distinctions in tags, `genre_matrix`, or `style_exemplars.category`, not in `style_type`.

When using style exemplars, treat them as anchors rather than source material:

- Use them to imitate rhythm, judgment posture, explanation order, and paragraph breath.
- Do not copy their factual content into the new draft.
- Prefer matching categories such as `opening`, `judgment`, `mechanism`, `counterargument`, `tutorial`, `investment`, `product-note`, `ending`, or `revision-gold`.
- If no exemplar matches, apply the profile rules without forcing an unrelated sample.

If no style reference is provided, use this default:

- Write like a practitioner sharing a tested workflow.
- Prefer concrete process over motivational advice.
- Prefer mechanisms over slogans.
- Avoid overused terms: `赋能`, `闭环`, `底层逻辑`, `打造个人IP`, `降本增效`, `破局`, `矩阵`.
- Avoid fake reader mind-reading such as `你可能会觉得`.
- Avoid fake statistics such as `90%的人`.
- Avoid excessive one-line dramatic paragraphs.
- Keep examples and caveats close to the claim they explain.

## Review Before Revise

For publication-quality output, review is a required step before revision. The review must use the resolved style profile, not only general writing taste.

Use `syntara_style_profile` with `action: "prepare_review"` after the first draft when the tool is available. The returned review packet should guide the review memo. If the action is unavailable, manually assemble the same inputs: `profile_markdown`, selected `style_exemplars`, anti-AI rules, revision preferences, source package, argument plan, and draft.

The review memo must separate:

- argument problems;
- evidence/source-boundary problems;
- structure problems;
- style/profile/exemplar alignment problems;
- AI-pattern problems;
- what to preserve.

Do not revise directly from the review memo. Write a revision plan first, then revise only according to that plan.

For polish, rewrite, or de-AI tasks over user-owned prose, also apply `human-revision-gate.md`:

- Change only what creates real friction, evidence risk, or style-profile conflict.
- Treat roughness, repeated words, particles, and uneven rhythm as possible author voice.
- Check only sentences changed or added by Syntara; do not treat untouched user prose as AI output.
- If a polished sentence feels more generic than the original, restore the original or make a smaller edit.

## Learning Gate

Do not update a Syntara style profile from AI-only review or revision output. Learning requires human material:

- user comments;
- user review notes;
- a user-edited/final version;
- a diff between AI draft and user final text.

When human material is available, use `syntara_style_profile` with `action: "learn_from_human_review"` or the existing revision update. If only AI review or AI revision exists, do not learn yet.

If the user asks for the user's own voice, and no style corpus is available, ask for prior drafts or representative paragraphs. For quick drafts, state that the voice pass is provisional.

## Evidence Notes

Use one of these evidence-note shapes:

### File-Level Note

Use when the connector provides source names but no page numbers.

```text
主要依据：文件A；文件B；文件C。
需人工核对：具体页码、表格数值、直接引语。
```

### Claim-Level Note

Use for professional, academic, or technical drafts.

```text
...正文句子。（依据：文件A；文件B）
```

### Manual Verification List

Use whenever the draft includes numbers, exact terms, direct quotes, or citation-sensitive claims.

```text
需要人工核对：
1. 数据X在原PDF中的页码和表格位置。
2. 术语Y在原文中的准确译法。
3. 引文Z是否为原文直接表述。
```

## Failure Modes To Avoid

- Declaring a knowledge base empty after one malformed call.
- Using local files after the user asked to use only cloud knowledge base materials.
- Treating search snippets as full-text evidence.
- Blending several sources into one unsupported claim.
- Writing a polished article while hiding unresolved evidence gaps.
- Creating page numbers or quote locations that the connector did not return.
- Ignoring the user's requested scope because a broader source is easier to access.
- Reading style samples directly but failing to save or reuse a Syntara style profile when the task asks for personal voice, style corpus, or durable style setup.
- Over-polishing user prose until the author's position, rhythm, hesitation, or plainness disappears.
