# Syntara MCP Tools For Reviews

Use these tools with a consistent `project` slug whenever possible.

- `syntara_list_projects`: choose an existing project area.
- `syntara_project_summary`: check counts for one project.
- `syntara_search_literature_grouped`: discover papers and chunk-level evidence for a review theme.
- `syntara_get_chunk_context`: verify that a hit truly supports the claim.
- `syntara_rag_answer`: answer one bounded evidence question; do not use it to draft the whole review.
- `syntara_search_pubmed`: find candidate PubMed records.
- `syntara_import_pubmed`: import selected PMIDs into the chosen project.
- `syntara_import_literature_pdfs`: import local full-text PDFs into the chosen project.
- `syntara_list_literature`: inspect project sources and citation metadata.
- `syntara_export_bibtex`: export references after cite keys are stable.

For review writing, prefer this order:

1. List or confirm project.
2. Search grouped literature by theme.
3. Open context for key chunks.
4. Build synthesis matrix.
5. Use RAG only for narrow unresolved questions.
6. Draft from the synthesis matrix.
7. Export or format citations at the end.
