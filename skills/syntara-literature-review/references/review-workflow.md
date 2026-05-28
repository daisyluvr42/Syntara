# Literature Review Workflow

## Frame The Review

Convert the user's topic into:

- Review question
- Target audience
- Inclusion boundaries
- Exclusion boundaries
- Key concepts and synonyms
- Expected output shape

Do this lightly for narrative reviews. Do it more explicitly for scoping-style or research-background reviews.

## Retrieval Strands

Use multiple focused Syntara queries instead of one broad prompt:

- Definition and conceptual boundary
- Core mechanism or causal pathway
- Application/clinical context
- Methods and measurement
- Evidence strength and limitations
- Controversies or inconsistent findings
- Recent updates
- Research gaps

Use `project` in every Syntara MCP call when the tool supports it.

## Source Handling

Separate:

- Primary evidence: original studies, trials, cohorts, mechanistic papers
- Secondary evidence: reviews, guidelines, consensus papers
- User corpus: notes, outlines, prior drafts, Tencent Docs material

Do not cite user notes as formal literature unless they point to a traceable source. Use notes to shape questions, structure, and emphasis.

## Draft Logic

A strong review should not summarize papers one by one. It should:

- define the problem
- group findings by theme or mechanism
- compare agreement and disagreement
- state what the evidence can and cannot support
- explain why the gap matters

Use paper-by-paper narration only for a short history section or when the user explicitly asks for an annotated bibliography.
