# Search And Import Status Design

## Goals

- Replace the current citation-only search list with a literature-first evidence browser.
- Support separate Chinese and English search inputs.
- When only one language is provided, keep the original query and use AI to fill the missing language when possible.
- Group results by literature, not by flat hit rows.
- Keep the sidebar compact while allowing full hit inspection in a dialog.
- Make import success observable beyond metadata creation.
- Expose semantic-search degradation instead of silently falling back.
- Move the backend default port to `8888`.

## Approved UX

- The search sidebar shows one card per literature item.
- Each card contains a checkbox for citation selection and a clickable body for opening hit details.
- The collapsed card shows title, authors/year, hit count, and one short preview.
- The details dialog shows all matching chunks for that literature.
- Each chunk keeps original text, heading, and page number.
- Highlight only terms that truly occur in the chunk text.
- Each chunk is copyable, and the dialog also supports inserting the current literature as a citation.
- Batch citation insertion remains available from the sidebar.

## Search Behavior

- Two input fields: `zh_query` and `en_query`.
- Both provided: search both as-is.
- Only one provided: search the provided query and ask AI to fill the other language.
- If AI query completion fails, continue with the provided query only.
- Semantic search still runs whenever embeddings are available.
- If embeddings are unavailable, the API reports that search degraded to keyword-only mode.

## Backend Shape

- Add literature processing fields:
  - `processing_status`
  - `processing_error`
  - `search_ready_fts`
  - `search_ready_vector`
- Import pipeline writes those fields based on actual extraction and indexing outcomes.
- Add grouped literature search endpoint returning:
  - query metadata and warnings
  - one result per literature
  - all matching chunks for that literature

## Frontend Shape

- Library panel shows processing state and search-readiness badges.
- Search panel switches from flat results to grouped literature cards.
- Details dialog consumes the grouped result directly from the search response.

## Non-Goals

- No search history.
- No saved filters.
- No pagination redesign.
- No separate legacy citation-results panel.
