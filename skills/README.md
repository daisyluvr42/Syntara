# Syntara Skills

Syntara Skills are the writing layer over the local evidence engine.

## Relationship

```text
syntara-writing
  -> resolves source scope, style mode, evidence discipline, and general drafting
  -> calls syntara-style-profiler when reusable user voice is needed
  -> handles articles, chapters, reviews, reports, scripts, and briefs as internal writing modes
```

## Skills

- `syntara-writing`: unified entrypoint for source-based writing, style reuse, de-AI passes, articles, chapters, reviews, reports, scripts, and mixed knowledge-base workflows.
- `syntara-style-profiler`: extracts, updates, and saves reusable Markdown + JSON style profiles from user-owned writing.

## Shared Behavior

- Use Syntara MCP as the evidence and retrieval layer.
- Keep final drafting in the host agent conversation unless the user asks otherwise.
- Resolve style before formal drafting.
- Use `syntara-writing/references/human-revision-gate.md` when polishing user-owned prose so the author hand is not smoothed away.
