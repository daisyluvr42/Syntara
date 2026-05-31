# Syntara MCP Tools For Reviews

Use the smallest sufficient Syntara tool call and pass a consistent `project` slug whenever possible.

## Readiness Rules

- `search_ready_fts: true` means full-text search can be used for review evidence.
- `search_ready_vector: false` only means vector/RAG retrieval is incomplete.
- When vector retrieval is not ready, continue with grouped full-text search and chunk context.
- Do not say Syntara search is unavailable unless source listing and full-text search both fail.
- Do not draft a finished review from general knowledge when Syntara evidence is missing.

## Tool Map

- `syntara_status`: use `action: "list_projects"` to choose a project and `action: "project_summary"` to inspect counts.
- `syntara_retrieve`: use `mode: "literature_grouped"` for source discovery, `mode: "chunk_context"` for support checks, `mode: "search"` for broad search, and `mode: "rag_answer"` only for bounded evidence questions.
- `syntara_external_search`: use `provider: "pubmed"` to find candidate PubMed records.
- `syntara_import`: use `source_type: "pubmed"` for PMIDs and `source_type: "literature_pdfs"` for local full-text PDFs.
- `syntara_sources`: use `source_type: "literature"` to inspect project sources and citation metadata.
- `syntara_style_profile`: use `action: "list"` / `"get"` for review style profiles and `action: "build"` / `"save"` when creating one from user-owned writing samples.
- `syntara_citations`: use `action: "export_bibtex"` or `action: "format"` after cite keys are stable.

## Review Order

1. Confirm the project.
2. Load the project default style profile if the task is formal writing.
3. Search grouped literature by theme.
4. Open context for key chunks.
5. Build synthesis matrix.
6. Use RAG only for narrow unresolved questions. If vector status is not ready, skip RAG and keep using full-text search plus chunk context.
7. Draft from the synthesis matrix.
8. Export or format citations at the end.
