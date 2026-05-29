# Syntara MCP Tools For Reviews

Use these tools with a consistent `project` slug whenever possible.

## Readiness Rules

- `search_ready_fts: true` means full-text search can be used for review evidence.
- `search_ready_vector: false` only means vector/RAG retrieval is incomplete.
- When vector retrieval is not ready, use grouped full-text search and chunk context.
- Do not say Syntara search is unavailable unless source listing and full-text search both fail.
- Do not draft a finished review from general knowledge when Syntara evidence is missing.

- `syntara_list_projects`: choose an existing project area.
- `syntara_project_summary`: check counts for one project.
- `syntara_search_literature_grouped`: discover papers and chunk-level evidence for a review theme.
- `syntara_get_chunk_context`: verify that a hit truly supports the claim.
- `syntara_rag_answer`: answer one bounded evidence question; do not use it to draft the whole review.
- `syntara_search_pubmed`: find candidate PubMed records.
- `syntara_import_pubmed`: import selected PMIDs into the chosen project.
- `syntara_import_literature_pdfs`: import local full-text PDFs into the chosen project.
- `syntara_list_literature`: inspect project sources and citation metadata.
- `syntara_get_style_profile`: load the default or named writing style profile for the review project.
- `syntara_list_style_profiles`: inspect reusable writing styles available for the project.
- `syntara_build_style_profile`: create a reusable style profile from user-owned review/chapter/article corpus.
- `syntara_save_style_profile`: save a profile extracted by WorkBuddy or imported from a maintained Markdown style document.
- `syntara_export_bibtex`: export references after cite keys are stable.

For review writing, prefer this order:

1. List or confirm project.
2. Load the project default style profile if the task is formal writing.
3. Search grouped literature by theme.
4. Open context for key chunks.
5. Build synthesis matrix.
6. Use RAG only for narrow unresolved questions. If vector status is not ready, skip RAG and keep using full-text search plus chunk context.
7. Draft from the synthesis matrix.
8. Export or format citations at the end.
