# Syntara MCP Tools

Use these tools as the local evidence and style layer for academic/professional writing. Keep the user's visible workflow the same: choose a Syntara skill, name the `project`, then let the skill retrieve evidence, resolve style, draft, and check citations.

## Readiness

- If `search_ready_vector: false`, only vector/RAG retrieval is incomplete.
- Continue with `syntara_retrieve` using `mode: "search"`, `mode: "literature_grouped"`, and `mode: "chunk_context"`.
- Do not draft from clinical or academic common sense when Syntara evidence is missing. Return an outline, partial draft, search report, or `待补证据`.

## Current Tool Surface

### `syntara_status`

Use for project and backend status.

- `action: "health"`: check backend health.
- `action: "list_projects"`: list project areas.
- `action: "project_summary"` with `project`: inspect one project.

### `syntara_retrieve`

Use for evidence retrieval.

- `mode: "search"` with `query`, `scope`, `top_k`, optional `project`.
- `mode: "literature_grouped"` with `zh_query` / `en_query`, `top_k`, optional `project`.
- `mode: "chunk_context"` with `lit_id` and `chunk_index`.
- `mode: "rag_answer"` with `question`, `search_scope`, `top_k`, optional `project`.

Use RAG only for bounded subquestions. For source gathering, prefer search and chunk context.

### `syntara_sources`

Use for inventory.

- `source_type: "literature"`: list formal sources and citation metadata.
- `source_type: "corpus"`: list notes, drafts, style samples, or other non-citation corpus items.

### `syntara_import`

Use for durable local imports.

- `source_type: "literature_pdfs"` with `file_paths` or `folder_path`.
- `source_type: "pubmed"` with `pmids`.
- `source_type: "corpus_text"` with `title` and `content`.

Use literature imports for citable papers. Use corpus imports for notes, outlines, Tencent Docs content, prior drafts, and style samples.

### `syntara_external_search`

Use as the external search entrypoint before import.

- `provider: "pubmed"` with `query` and `max_results`.

When another provider is added, it should appear here as a new `provider`, not as a new top-level tool.

### `syntara_style_profile`

Use for reusable writing style.

- `action: "list"`: inspect profiles by `project` and optional `style_type`.
- `action: "get"`: load a profile by `profile_id`, name, or `default: true`.
- `action: "build"`: extract a profile from Syntara corpus ids, tag, or direct `content`.
- `action: "save"`: save a Markdown + JSON profile extracted in the conversation.
- `action: "update_from_revision"`: learn durable preferences from original vs user-revised text.
- `action: "set_default"`: set a profile as project default.

For formal writing, load `profile_markdown` before outlining. Listing the profile is not enough.

### `syntara_citations`

Use after cite keys are stable.

- `action: "format"` with `content` and `style`.
- `action: "export_bibtex"` with `cite_keys`.

## Common Flows

### Evidence-backed chapter

1. `syntara_status` with `action: "project_summary"`.
2. `syntara_style_profile` with `action: "get"` and `default: true`.
3. `syntara_retrieve` with `mode: "literature_grouped"` for each claim cluster.
4. `syntara_retrieve` with `mode: "chunk_context"` for important support.
5. Draft in the writing skill, not as pasted RAG output.
6. `syntara_citations` at the end.

### Import new academic sources

1. Local PDFs: `syntara_import` with `source_type: "literature_pdfs"`.
2. PubMed: `syntara_external_search` with `provider: "pubmed"`, then `syntara_import` with `source_type: "pubmed"`.
3. User notes or style samples: `syntara_import` with `source_type: "corpus_text"`.

### Build or update style

1. `syntara_style_profile` with `action: "list"` and the inferred `style_type`.
2. If no suitable profile exists, use `syntara-style-profiler`.
3. The profiler calls `syntara_style_profile` with `action: "build"` or `action: "save"`.
4. If learning from edits, it calls `action: "update_from_revision"`.
