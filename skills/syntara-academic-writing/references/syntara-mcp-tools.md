# Syntara MCP Tool Contract

Use this reference when calling the connected Syntara MCP server from WorkBuddy.

Exact tool names may differ. Match by semantics.

## Readiness Rules

- `search_ready_fts: true` means full-text/keyword retrieval can be used.
- `search_ready_vector: false` means vector retrieval or RAG may be incomplete. It does not mean Syntara evidence retrieval is unavailable.
- When vector search is not ready, use `syntara_search`, `syntara_search_literature_grouped`, and `syntara_get_chunk_context` as the evidence path.
- Do not tell the user that Syntara search is unavailable unless both full-text search and source listing fail.
- Do not draft evidence-backed prose from general knowledge just because vector search is unavailable.

## Expected Tools

### `syntara_list_projects`

Purpose: list Syntara project areas. Projects are backed by `project:<slug>` tags.

Use for: choosing the right project before retrieval or import.

### `syntara_project_summary`

Purpose: inspect literature and corpus counts for one project.

Input:

```json
{
  "project": "professional-book"
}
```

Use for: confirming whether a project already has enough material.

### `syntara_search`

Purpose: find evidence candidates in Syntara literature and/or corpus.

Input:

```json
{
  "query": "clinical question or keyword query",
  "scope": "all | literature | corpus",
  "top_k": 10,
  "project": "optional project slug"
}
```

Expected output: ranked hits with title, source type, snippet/content, cite key if available, literature id, and chunk index.

Use for: first-pass evidence collection and style-corpus lookup.

### `syntara_rag_answer`

Purpose: answer one bounded question using Syntara retrieval.

Input:

```json
{
  "question": "narrow question",
  "search_scope": "all | literature | corpus",
  "top_k": 5,
  "use_tree": true,
  "project": "optional project slug"
}
```

Expected output: answer, sources, cited keys.

Use for: resolving a subquestion after search, not for writing the whole chapter.

### `syntara_search_literature_grouped`

Purpose: search literature and return document-level hits with chunk indexes.

Input:

```json
{
  "zh_query": "中文检索词",
  "en_query": "English query",
  "top_k": 10,
  "project": "optional project slug"
}
```

Expected output: literature records with cite keys, preview hit, and `hits[]` entries containing `chunk_index`, content, heading, page number, matched terms, and highlights.

Use for: source gathering when the next step may need `syntara_get_chunk_context`.

### `syntara_get_chunk_context`

Purpose: expand a hit to surrounding context.

Input:

```json
{
  "lit_id": "literature id",
  "chunk_index": 12
}
```

Expected output: surrounding text and metadata.

Use for: checking whether a snippet truly supports a claim.

### `syntara_list_literature` / `syntara_list_corpus`

Purpose: inspect available sources, tags, titles, or imported user corpus.

Use for: choosing evidence scope and verifying whether the user's prior book corpus is present.

### `syntara_import_corpus_text`

Purpose: import text retrieved from WorkBuddy `资料库` / Tencent Docs into the Syntara local corpus and build local FTS/vector indexes.

Input:

```json
{
  "title": "document title",
  "content": "markdown or plain text",
  "description": "optional source note",
  "tags": ["tencent-docs", "style-corpus"],
  "project": "professional-book",
  "source_url": "optional docs.qq.com URL",
  "source_id": "optional file_id or node_id",
  "dry_run": false
}
```

Expected output: Syntara corpus id and title.

Use for: turning cloud documents, user-prepared style corpus, or chapter notes into a reusable local Syntara corpus. Use `dry_run: true` when checking payload size or routing without writing.

### `syntara_build_style_profile`

Purpose: extract a reusable structured writing style profile from user corpus.

Input:

```json
{
  "name": "专业书章节风格",
  "project": "professional-book",
  "corpus_ids": ["optional corpus id"],
  "tag": "optional corpus tag",
  "content": "optional direct style corpus text",
  "source_title": "optional source title",
  "set_default": true
}
```

Use for: turning prior chapters, Tencent Docs drafts, WorkBuddy knowledge-base text, or other user-owned prose into a reusable Syntara style asset.

### `syntara_save_style_profile`

Purpose: save an already extracted profile as a reusable Syntara asset.

Use for: preserving a profile extracted by WorkBuddy when backend AI extraction is unavailable, or importing a hand-maintained Markdown style document.

### `syntara_list_style_profiles` / `syntara_get_style_profile` / `syntara_set_default_style_profile`

Purpose: discover, load, and bind reusable style profiles.

Use for: resolving writing style before outlining. For formal writing, first call `syntara_get_style_profile` with `default: true` for the chosen project. If none exists, list profiles and use a clear match. If no profile exists, use the default de-AI pass and mention that a reusable profile can be created from style samples.

### `syntara_search_pubmed`

Purpose: search PubMed through Syntara and return candidate articles with PMIDs.

Input:

```json
{
  "query": "alveolar ridge augmentation dental implant",
  "max_results": 20
}
```

Use for: finding candidate PubMed records before importing. Show the user titles/authors/PMIDs when the match is ambiguous.

### `syntara_import_pubmed`

Purpose: import selected PubMed records into the Syntara literature library.

Input:

```json
{
  "pmids": ["12345678", "23456789"],
  "project": "professional-book",
  "dry_run": false
}
```

Expected output: imported records with Syntara ids, cite keys, titles, and skipped duplicates.

Use for: adding article metadata and abstracts as formal literature. These records can support citation keys, but may not contain full text unless Syntara later has the PDF/full text.

### `syntara_import_literature_pdfs`

Purpose: import local PDF files into the Syntara literature library and start background extraction/indexing.

Input:

```json
{
  "file_paths": ["/absolute/path/paper.pdf"],
  "folder_path": "/optional/folder/of/pdfs",
  "recursive": false,
  "project": "professional-book",
  "dry_run": false
}
```

Expected output: imported PDF records with Syntara ids and cite keys, plus any failed files.

Use for: adding formal literature with full-text extraction. Prefer this for PDFs that should become citable RAG evidence.

### `syntara_format_citations`

Purpose: format inline citation keys or bibliography if exposed by the MCP server.

Use for: final cleanup only after the draft's evidence markers are stable.

## Calling Pattern

1. Choose or infer the project area.
2. Search broadly enough to find candidate sources, passing `project` when available.
3. Open context for the most important hits.
4. Ask RAG only narrow questions. If RAG/vector status is not ready, skip RAG and continue with grouped full-text search plus chunk context.
5. If a cloud document should become durable local corpus, import it with `syntara_import_corpus_text`, then search it with `scope: "corpus"` or `scope: "all"`.
6. If the user wants to add formal literature, use PDF import for local files or PubMed search/import for PMIDs.
7. Keep an evidence ledger outside the prose.
8. Draft from the ledger, not directly from raw RAG output.
