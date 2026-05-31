# Style Extraction

Use this reference when the user provides prior professional-book chapters or sections, or when Syntara MCP returns a reusable style profile.

## Prefer Reusable Profiles

For formal chapter writing, first look for a Syntara style profile:

1. Call `syntara_style_profile` with `action: "list"`, the current `project`, and `style_type: "professional-book"` if available.
2. If no type-specific profile exists, call `syntara_style_profile` with `action: "get"`, the current `project`, and `default: true`.
3. If no default exists, call `syntara_style_profile` with `action: "list"` for the project.
4. If no suitable profile exists, look for professional-book style samples in the current corpus or connected knowledge base. Likely labels include `style-corpus`, `书稿`, `章节`, `旧章节`, `专业书`, `草稿`, or `voice`.
5. If exactly one obvious style source is found, use `syntara-style-profiler` to build and save a `professional-book` Markdown + JSON project default profile before outlining. If several candidates are found, ask the user to choose.
6. If the user provides style corpus and no suitable profile exists, run the `syntara-style-profiler` workflow before outlining. It may call `syntara_style_profile` with `action: "build"`, or extract in the conversation and save with `action: "save"` when backend AI is unavailable.
7. Apply the returned profile as the style brief.

Only do ad hoc style extraction inside the conversation when MCP style tools are unavailable, and still save a non-empty Markdown + JSON profile once saving is possible.

## Extract A Style Brief

Read enough source prose to capture repeatable habits. Do not turn one unusual paragraph into a universal rule.

Capture:

- Reader position: specialist peer, resident, general clinician, or patient-facing.
- Explanation order: concept first, clinical problem first, case scene first, or literature first.
- Sentence rhythm: long analytic paragraphs, short didactic statements, mixed cadence.
- Claim posture: cautious, experience-led, guideline-led, mechanism-led, or argumentative.
- Terminology rules: Chinese/English terms, abbreviations, preferred translations, recurring definitions.
- Evidence handling: how citations appear, how literature is introduced, how uncertainty is stated.
- Teaching devices: analogies, case fragments, lists, warnings, definitions, "临床要点" style summaries.
- Prohibited drift: AI-sounding transitions, generic academic boilerplate, overconfident claims without evidence.

## Produce A Brief Before Drafting

Use this compact shape:

```text
写作风格画像
- 读者与语气:
- 解释顺序:
- 段落和句式:
- 术语习惯:
- 文献进入方式:
- 经验判断边界:
- 写作禁忌:
```

Keep the brief short enough to remain usable during drafting.

## Apply The Brief

During drafting, use the style brief as a constraint, not as decorative text. The chapter should sound like the source corpus through structure, explanation sequence, and claim discipline, not through copied phrases.

Do not imitate private or copyrighted passages verbatim unless the user explicitly asks to reuse their own text.
