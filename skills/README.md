# Syntara Skills

Syntara Skills are the writing layer over the local evidence engine.

## Relationship

```text
syntara-knowledge-writing
  -> resolves source scope, style mode, evidence discipline, and general drafting
  -> calls syntara-style-profiler when reusable user voice is needed
  -> hands off to syntara-academic-writing for professional book chapters
  -> hands off to syntara-literature-review for review synthesis
```

## Skills

- `syntara-knowledge-writing`: default entrypoint for source-based writing, style reuse, de-AI passes, and mixed knowledge-base workflows.
- `syntara-style-profiler`: extracts, updates, and saves reusable Markdown + JSON style profiles from user-owned writing.
- `syntara-academic-writing`: drafts professional book chapters and academic longform with Syntara evidence.
- `syntara-literature-review`: builds literature reviews, related-work sections, and research-gap syntheses.

## Shared Behavior

- Use Syntara MCP as the evidence and retrieval layer.
- Keep final drafting in the host agent conversation unless the user asks otherwise.
- Resolve style before formal drafting.
- Use `syntara-knowledge-writing/references/human-revision-gate.md` when polishing user-owned prose so the author hand is not smoothed away.
