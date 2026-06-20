# Syntara MCP Tools For Knowledge Writing

Use Syntara MCP as the local source, style, and citation layer. Use the smallest tool call that answers the current step.

## Tool Map

- `syntara_status`: check backend health, list projects, or inspect one project summary.
- `syntara_sources`: list literature or corpus inventory inside the chosen project or tag.
- `syntara_retrieve`: search evidence, ask bounded RAG questions, run grouped literature search, or open chunk context.
- `syntara_import`: import user notes/style samples as corpus text, import local PDFs as literature, or import PubMed records.
- `syntara_style_profile`: list, get, build, save, update from revision, prepare a style-aware review packet, learn from human-reviewed feedback/final text, or set default style profiles.
- `syntara_external_search`: search external academic providers before import.
- `syntara_citations`: format citations or export BibTeX after cite keys are stable.

## Order

1. Use `syntara_status` or `syntara_sources` to confirm project and source scope.
2. Use `syntara_style_profile` to resolve the style profile before formal drafting.
3. Use `syntara_retrieve` for evidence and context.
4. After drafting, use `syntara_style_profile` with `action: "prepare_review"` before revising any publication-quality output.
5. Use `syntara_style_profile` with `action: "learn_from_human_review"` only after the user provides feedback, comments, or an edited/final version.
6. Use `syntara_import` only when the user wants material added durably.
7. Use `syntara_citations` at the end, after evidence and cite keys are stable.

Do not paste a RAG answer as final prose. Use retrieval output as evidence, then draft in the writing Skill.
