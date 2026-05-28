# Syntara Writing Skill Extension Interface

Use this reference when adding a new writing-form Skill that uses the same Syntara MCP backend.

## Stable Split

- The writing-form Skill owns genre rules, style constraints, section shape, revision standards, and final prose.
- Syntara MCP owns project areas, literature/corpus import, retrieval, RAG, chunk context, citations, and exports.
- WorkBuddy owns the user-facing conversation, cloud `资料库`, Tencent Docs access, and task context.

## Required Skill Sections

Each new writing-form Skill should define:

- Trigger: when this genre Skill should be used.
- Inputs: topic, audience, output shape, project slug, evidence scope, style corpus, citation style.
- Retrieval plan: how to turn the writing task into Syntara search/RAG questions.
- Evidence discipline: which claims need literature and which can be user judgment or draft context.
- Draft shape: the expected headings, sections, and final deliverables.
- Final checks: unsupported claims, citation markers, style fidelity, and terminology consistency.

## Project Contract

Use one `project` slug throughout a task. If no project is named, infer a concise slug and ask before durable imports.

Recommended tags:

- `project:<slug>`: required for project-scoped material
- `literature`: formal papers, books, PDFs, PubMed records
- `style-corpus`: high-quality user prose for style extraction
- `outline`: user-prepared structure or chapter plan
- `notes`: reading notes, Tencent Docs notes, meeting notes
- `draft`: previous draft or intermediate generated text
- `review-target`: text being reviewed or revised

## Minimal New Skill Template

```markdown
---
name: syntara-<genre>
description: Use this skill when ...
---

# Syntara <Genre>

## Boundary

Use WorkBuddy for conversation, this Skill for <genre> writing logic, and Syntara MCP for project-scoped RAG.

## Inputs

- Topic/question
- Output type and reader
- Syntara project slug
- Evidence scope
- Style corpus

## Workflow

1. Identify project and material scope.
2. Extract genre/style constraints.
3. Build claim clusters and retrieval questions.
4. Retrieve with Syntara MCP using `project`.
5. Build an evidence ledger.
6. Draft in the genre's structure.
7. Run citation and style checks.
```

Keep each new Skill small. Put genre-specific detail in `references/` and reuse the MCP project contract instead of redefining backend behavior.
