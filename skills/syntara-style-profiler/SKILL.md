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
- saving a reusable Markdown + JSON profile with Syntara MCP;
- setting the correct project default when appropriate.

Do not write the requested article, chapter, review, or deck. After saving the profile, hand off to a writing Skill such as `syntara-knowledge-writing`, `syntara-academic-writing`, or `syntara-literature-review`.

## Trigger Behavior

When the user names a corpus folder, old drafts, prior articles, Tencent Docs/ima/WorkBuddy materials, or says to learn/extract/update their style, run this Skill before writing.

If a writing task includes both source materials and a new style corpus, perform this style-profile workflow first unless the user explicitly says not to save or update style.

## Required Outputs

Every saved style profile must include both:

- `profile_markdown`: a human-readable style document.
- `profile_json`: a compact structured object that downstream Skills can inspect.

Do not save an empty `{}` profile_json unless the user explicitly asks for Markdown-only import.

## Workflow

1. Resolve scope:
   - Source location: local folder/files, ima knowledge base, Tencent Docs, WorkBuddy `资料库`, or Syntara corpus.
   - Syntara `project`: use the user-specified project, infer from context, or use `default`.
   - `style_type`: infer from corpus and target form, such as `wechat-longform`, `professional-book`, `literature-review`, `tutorial`, `report`, `script`, `ppt`, or `general`.

2. Inventory the corpus:
   - List files/documents first.
   - Prefer user-owned prose. Do not treat literature PDFs, research sources, or third-party examples as user voice unless the user explicitly asks to imitate them.
   - If the corpus mixes genres, group by `style_type` and build separate profiles. Do not merge professional chapters, public essays, tutorials, slide scripts, and social posts into one profile unless the user asks for a house style.

3. Read enough material:
   - For small corpora, read all files.
   - For larger corpora, read a representative set across time, topic, and genre; include at least 5 substantial samples when available.
   - Preserve exact source filenames in the profile metadata.

4. Check existing Syntara profiles:
   - Call `syntara_list_style_profiles` with `project` and `style_type` when possible.
   - If updating an existing profile, call `syntara_get_style_profile` with `profile_id`, not `id`.
   - Compare the old profile with the new corpus findings. Preserve useful existing rules unless contradicted by the corpus.

5. Extract along fixed dimensions:
   - overall tone;
   - opening patterns;
   - structure and section rhythm;
   - paragraph and sentence rhythm;
   - claim style and argument flow;
   - evidence and fact discipline;
   - vocabulary preferences;
   - banned words, phrases, and AI-like moves;
   - formatting and visual habits;
   - genre-specific variants;
   - revision and final-pass checklist.

6. Produce `profile_json`:
   - Use the schema in `references/profile-schema.md`.
   - Keep JSON compact and practical. Put long explanations in Markdown, not JSON.
   - Include `source_count`, `source_titles`, `project`, `style_type`, and `updated_from_profile_id` when applicable.

7. Produce `profile_markdown`:
   - Use `references/profile-template.md`.
   - The Markdown must be directly usable as a writing brief.
   - Include concrete examples only when short and necessary.

8. Persist:
   - Prefer `syntara_build_style_profile` when Syntara backend AI extraction is configured and the corpus content or corpus ids are available.
   - If WorkBuddy has already performed the extraction, call `syntara_save_style_profile` with `name`, `project`, `style_type`, `profile_json`, `profile_markdown`, useful `tags`, and `set_default`.
   - If the visible WorkBuddy tool name is prefixed, use the equivalent `mcp__syntara__syntara_save_style_profile` / `syntara_syntara_save_style_profile`.

9. Report:
   - Return the saved profile id.
   - State whether it was set as default.
   - Summarize the main changes and the source corpus used.
   - If multiple style profiles should be created but only one was saved, list the remaining candidates.

## Safety Rules

- Never fabricate style traits that are not supported by the corpus.
- Do not overfit one unusual article unless the user selected it as the style target.
- Do not turn factual sources into user voice.
- Do not overwrite the old profile in place unless Syntara MCP explicitly supports update semantics. Saving a new version and making it default is acceptable.
- If the user asks only to inspect style without saving, provide the profile draft but do not call save.

## References

- `references/profile-schema.md`: required JSON shape.
- `references/profile-template.md`: Markdown profile layout.
