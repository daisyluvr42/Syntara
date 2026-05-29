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

1. Infer `style_type` from the requested output: `wechat-longform`, `professional-book`, `literature-review`, `tutorial`, `report`, `script`, `ppt`, or `general`.
2. Use `syntara_list_style_profiles` with the inferred project and `style_type` when available. In WorkBuddy custom MCP, the visible name may be `syntara_syntara_list_style_profiles`.
3. If no type-specific profile is found, use `syntara_get_style_profile` with `default: true` for the inferred project.
4. If not found, use `syntara_list_style_profiles` without a project filter and choose a clear single/default match.
5. After choosing a listed profile, call `syntara_get_style_profile` for its id. Do not draft from the list summary alone.
6. If no profile exists, run first-use style setup:
   - Search the available user-owned corpus or connected knowledge base for likely style samples: `style-corpus`, `style`, `风格`, `旧文`, `往期文章`, `代表作`, `书稿`, `章节`, `公众号`, `草稿`, `voice`.
   - If the style corpus contains different genres or writing types, group by style type and build separate profiles.
   - If exactly one obvious style source is found, use `syntara-style-profiler` to extract and save a Markdown + JSON project default profile with the inferred `style_type`.
   - If multiple candidates are found, ask the user to choose.
   - If none are found, continue only with `default_de_ai` unless the user asked for their own voice, in which case ask for 2-5 representative drafts or a folder/document location.
7. If the task includes style corpus, route style extraction through `syntara-style-profiler`; it should save a normalized profile with `syntara_build_style_profile` or `syntara_save_style_profile`.
8. If no profile exists and the user wants to continue, keep writing with `default_de_ai` and state that this is not the user's personal voice.

Before drafting, choose one style mode:

- `user_voice`: when a Syntara style profile, prior drafts, representative paragraphs, or an explicit user-style corpus are available.
- `named_style`: when the prompt names a publication, author, genre, or house style.
- `source_document_style`: only when the user explicitly asks to imitate the uploaded sources' prose.
- `default_de_ai`: when no style source is specified.

Do not silently skip style. If no style reference or Syntara profile is available, use `default_de_ai` rather than the user's personal voice.

If no style reference is provided, use this default:

- Write like a practitioner sharing a tested workflow.
- Prefer concrete process over motivational advice.
- Prefer mechanisms over slogans.
- Avoid overused terms: `赋能`, `闭环`, `底层逻辑`, `打造个人IP`, `降本增效`, `破局`, `矩阵`.
- Avoid fake reader mind-reading such as `你可能会觉得`.
- Avoid fake statistics such as `90%的人`.
- Avoid excessive one-line dramatic paragraphs.
- Keep examples and caveats close to the claim they explain.

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
