# Tencent Docs Corpus

Use this reference when WorkBuddy has Tencent Docs material available through its native `资料库` panel or the installed `tencent-docs` skill.

## Role In The Workflow

WorkBuddy `资料库` is the cloud corpus layer. Use Tencent Docs material for:

- living chapter outlines
- user notes and rough drafts
- prior professional-book passages
- terminology lists
- collaborator comments
- style examples that update over time

Syntara remains the local evidence corpus for literature RAG, source context, and citation keys.

If the source is a paper PDF or PubMed article, do not import it as Tencent Docs corpus. Add it to the Syntara literature library instead.

## How To Connect It With This Skill

Use a three-part handoff:

1. WorkBuddy `资料库` / `tencent-docs` retrieves cloud material.
2. This skill classifies and distills that material into writing constraints.
3. Syntara MCP retrieves literature evidence for factual claims.

The skill should not reimplement Tencent Docs access. When cloud material is needed:

- If the user already attached or selected Tencent Docs material in the task, read it from the current WorkBuddy context.
- If the user names documents or asks to search cloud docs, use the installed `tencent-docs` skill. Its common pattern is `manage.search_file` to find files, then `get_content` to read them.
- If the material lives inside a Tencent Docs knowledge-base space, use the Tencent Docs space workflow: `query_space_list` -> `query_space_node` -> `get_content` by `node_id` / `file_id`.

## Importing Cloud Corpus Into Syntara

When the user wants Tencent Docs material to become reusable local corpus, call Syntara MCP after reading the cloud document:

```json
{
  "tool": "syntara_import_corpus_text",
  "arguments": {
    "title": "original Tencent Docs title",
    "content": "content returned by get_content",
    "description": "Imported from WorkBuddy 资料库 / Tencent Docs",
    "tags": ["tencent-docs", "style-corpus"],
    "project": "professional-book",
    "source_url": "optional docs URL",
    "source_id": "optional file_id/node_id"
  }
}
```

Use tags deliberately:

- `style-corpus`: prior user prose for style extraction
- `chapter-notes`: outline, notes, or draft material
- `terminology`: term lists or preferred translations
- `evidence-note`: user-curated excerpts that still need original citation verification

## Source Discipline

Classify every retrieved item before drafting:

- `style`: prior user prose used to infer voice and explanation habits
- `outline`: requested structure or chapter plan
- `note`: user thinking, clinical experience, or TODO material
- `evidence`: only if the document itself contains traceable literature or imported source excerpts

Do not cite Tencent Docs notes as literature. If a Tencent Docs note points to a paper, use Syntara or the original source to retrieve citation metadata.

## Adding Formal Literature From WorkBuddy

Use these routes for citable sources:

- Local PDFs: call `syntara_import_literature_pdfs` with `file_paths` or `folder_path`.
- PubMed records: call `syntara_search_pubmed` to find PMIDs, then `syntara_import_pubmed`.
- Tencent Docs notes that mention papers: extract DOI/PMID/title from the note, then add the original paper through Syntara literature tools.

## Writing Pattern

1. Read WorkBuddy `资料库` / Tencent Docs material first to understand the user's current intent and style.
2. Choose the Syntara project slug for this task.
3. Extract a compact style brief and outline constraints.
4. Use Syntara MCP to retrieve literature evidence for each claim cluster, passing `project` when available.
5. Draft with Tencent Docs shaping prose and Syntara anchoring factual claims.

## Good Use

Use Tencent Docs for material that changes often or benefits from collaboration. Keep stable literature, PDFs, citation keys, and source context in Syntara.
