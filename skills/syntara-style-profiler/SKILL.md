---
name: syntara-style-profiler
description: Use this skill to extract, update, normalize, and persist reusable Syntara writing style profiles from a user's own corpus. Trigger when the user mentions old writing, prior drafts, personal corpus, style corpus, 旧文, 往期文章, 语料, 风格语料, 提取风格, 沉淀风格, 更新profile, 保存风格档案, personal voice, author voice, house style, or asks Syntara/WorkBuddy to learn their writing style. This skill does not draft articles; it creates Markdown plus JSON style profiles for later Syntara MCP and writing-skill reuse.
---

# Syntara Style Profiler

## Role

Use this Skill as the dedicated Syntara style-extraction and style-profile persistence workflow.

Own:

- locating user-owned style corpus;
- grouping corpus by writing type;
- extracting a structured style profile;
- selecting short representative style exemplars;
- learning durable revision preferences from generated drafts and user-edited versions;
- saving a reusable Markdown + JSON profile with Syntara MCP;
- setting the correct project default when appropriate.

Do not write the requested article, chapter, review, or deck. After saving the profile, hand off to `syntara-writing`, the unified Syntara writing Skill.

## Trigger Behavior

When the user names a corpus folder, old drafts, prior articles, Tencent Docs/ima/WorkBuddy materials, or says to learn/extract/update their style, run this Skill before writing.

If a writing task includes both source materials and a new style corpus, perform this style-profile workflow first unless the user explicitly says not to save or update style.

When the user provides an original/generated draft plus their revised/final version, treat it as a revision-learning task. Extract the user's editing preferences and merge them into the existing Syntara style profile instead of creating a separate standalone diff note.

## Required Outputs

Every saved style profile must include both:

- `profile_markdown`: a human-readable style document.
- `profile_json`: a compact structured object that downstream Skills can inspect.

Do not save an empty `{}` profile_json unless the user explicitly asks for Markdown-only import.

## Workflow

1. Resolve scope:
   - Source location: local folder/files, ima knowledge base, Tencent Docs, WorkBuddy `资料库`, or Syntara corpus.
   - Syntara `project`: use the user-specified project, infer from context, or use `default`.
   - `writing_mode`: infer the dominant purpose using `references/style-taxonomy.md`.
   - `style_type`: infer the reusable document genre using `references/style-taxonomy.md`, such as `blog-article`, `academic-paper`, `literature-review`, `technical-report`, `business-report`, `white-paper`, `proposal`, `memo-email`, `documentation`, `instructional-guide`, `presentation`, `talk-script`, `reflection`, or `general`.

2. Inventory the corpus:
   - List files/documents first.
   - Resolve the corpus exactly from the user's prompt: folder path, file list, knowledge-base name, document title, project slug, or search criteria. If multiple plausible corpora match, ask or state the chosen match before extraction.
   - Treat an explicit user-provided path or file list as the corpus boundary. Do not search the current workspace, sibling folders, or earlier candidate folders for extra style samples unless the user asks to broaden the corpus.
   - Prefer user-owned prose. Do not treat literature PDFs, research sources, or third-party examples as user voice unless the user explicitly asks to imitate them.
   - Apply inclusion/exclusion rules only when the user states them or the corpus has an explicit manifest/readme that marks documents to include or exclude. Record the rule used.
   - If the corpus mixes genres, group by common `style_type` and build separate profiles. Do not merge academic papers, reports, instructions, public articles, presentations, social posts, and personal reflections into one profile unless the user asks for a house style.
   - Record both included and excluded source counts. `source_count` must equal the number of included files actually analyzed, and `source_titles` must be real included filenames/ids.

3. Read enough material:
   - For small corpora, read all files.
   - For larger corpora, read a representative set across time, topic, and genre; include at least 5 substantial samples when available.
   - For dated or sequential corpora, stratify by time period. Identify early/middle/recent samples and state which period should dominate future imitation. Do not average early abandoned habits into the current voice.
   - Preserve exact source filenames in the profile metadata.

4. Check existing Syntara profiles:
   - Call `syntara_style_profile` with `action: "list"`, `project`, and `style_type` when possible.
   - If updating an existing profile, call `syntara_style_profile` with `action: "get"` and `profile_id`, not `id`.
   - Compare the old profile with the new corpus findings. Preserve useful existing rules unless contradicted by the corpus.

5. Extract along fixed dimensions:
   - writer profile and source of voice;
   - overall tone;
   - tone spectrum by genre or context;
   - opening patterns;
   - structure and section rhythm;
   - paragraph and sentence rhythm;
   - claim style and argument flow;
   - evidence and fact discipline;
   - reader relationship and expectation management;
   - vocabulary preferences;
   - banned words, phrases, and AI-like moves;
   - formatting and visual habits;
   - common `writing_mode` and `style_type`;
   - cross-genre constants;
   - genre-specific variants;
   - style evolution and sample priority;
   - representative style exemplars for matching future tasks;
   - revision and final-pass checklist.
   For each important rule, include source evidence: at least one source filename and a short example or paraphrased example. Distinguish "appears in corpus" from "recommended preference"; do not promote low-frequency or user-disfavored AI-like phrases into positive lexicon preferences.
   Also select 3-8 short user-owned passages as `style_exemplars` when the corpus supports it. Use categories such as `opening`, `judgment`, `mechanism`, `transition`, `counterargument`, `tutorial`, `investment`, `product-note`, `ending`, or `revision-gold`. Each excerpt should be under 240 Chinese characters and paired with a note explaining the reusable rhythm, judgment posture, or structural move. Do not store third-party factual source passages as user voice exemplars.

6. Produce `profile_json`:
   - Use the schema in `references/profile-schema.md`.
   - Use the common taxonomy in `references/style-taxonomy.md`.
   - Keep JSON compact and practical. Put long explanations in Markdown, not JSON.
   - Include `source_count`, `source_titles`, `project`, `style_type`, `writing_mode`, and `updated_from_profile_id` when applicable.
   - Include `source.excluded_sources`, `style_exemplars`, `evidence`, `tone_spectrum`, `genre_matrix`, `reader_relationship`, and `style_evolution` when the corpus supports them.
   - Validate source consistency before saving: every `source_titles` entry must belong to the resolved corpus, user-excluded files must not appear in `source_titles`, and counts must match.

7. Produce `profile_markdown`:
   - Use `references/profile-template.md`.
   - The Markdown must be directly usable as a writing brief.
   - Include a `Style Exemplars` section with the selected short excerpts, their categories, source titles, and imitation notes.
   - Include concrete examples or tight paraphrases for the most important rules. Prefer short evidence over unsupported adjectives.
   - Include a source audit note: corpus path, included count, excluded count, sample strategy, and any uncertainty.

8. Persist:
   - Prefer `syntara_style_profile` with `action: "build"` when Syntara backend AI extraction is configured and the corpus content or corpus ids are available.
   - If WorkBuddy has already performed the extraction, call `syntara_style_profile` with `action: "save"`, `name`, `project`, `style_type`, `profile_json`, `profile_markdown`, useful `tags`, and `set_default`.

9. Report:
   - Return the saved profile id.
   - State whether it was set as default.
   - Summarize the main changes and the source corpus used.
   - If multiple style profiles should be created but only one was saved, list the remaining candidates.

## Revision Diff Workflow

Use this branch when the user says they edited the generated article/chapter/deck script, sends an "original vs revised" pair, or gives explicit review feedback on an AI draft.

1. Resolve the target style profile:
   - Use the user's `base_profile_id` if provided.
   - Otherwise call `syntara_style_profile` with `action: "get"`, the current `project`, and `default: true`.
   - If no default profile exists, still run the revision update so Syntara can create a first profile from the user's edits.

2. Compare only writing choices:
   - Learn what the user removed, compressed, expanded, reordered, renamed, softened, sharpened, or made more concrete.
   - Separate factual corrections from style rules. A corrected fact belongs to evidence discipline, not voice imitation.
   - Prefer durable preferences over one-off edits.
   - Pay special attention to AI-polish reversals: places where the user restored plainer wording, rougher rhythm, colloquial particles, direct repetition, hesitation, or a less "clever" sentence.
   - Record rejected AI-like moves such as meaning inflation, forced contrasts, slogan endings, invented scene/detail, decorative formatting, and over-balanced structures.
   - When the revised/final version contains a compact passage that should guide future drafts, add it as a `revision-gold` style exemplar instead of only describing it as a rule.

3. Call `syntara_style_profile` with `action: "learn_from_human_review"` when learning from a reviewed draft, or `action: "update_from_revision"` for a direct original/final pair:
   - `original_text`: the AI/generated draft before user edits.
   - `revised_text`: the user's edited/final version, when available.
   - `human_feedback`: the user's comments or review notes, when available.
   - `base_profile_id` when available.
   - `project`, `style_type`, `source_title`, and `set_default: true` unless the user asks not to update defaults.

4. Confirm the merged result:
   - Report the new profile id.
   - State that revision preferences were integrated into the profile Markdown and JSON.
   - Mention the highest-signal learned preferences, especially banned AI-like moves, over-polish patterns, and preferred revision habits.
   - Do not proceed to rewrite another draft unless the user asks.

## Safety Rules

- Never fabricate style traits that are not supported by the corpus.
- Never learn from AI-only review memos, AI revision plans, or AI second drafts. Learning requires user feedback or user-edited text.
- Do not overfit one unusual article unless the user selected it as the style target.
- Do not turn factual sources into user voice.
- Do not overwrite the old profile in place unless Syntara MCP explicitly supports update semantics. Saving a new version and making it default is acceptable.
- For revision diffs, do not save a separate "diff profile" when a base style profile exists. Merge the learned preferences into the next version of the same profile and make it the project default when appropriate.
- If the user asks only to inspect style without saving, provide the profile draft but do not call save.

## References

- `references/profile-schema.md`: required JSON shape.
- `references/profile-template.md`: Markdown profile layout.
- `references/style-taxonomy.md`: common writing modes and public style_type values.
