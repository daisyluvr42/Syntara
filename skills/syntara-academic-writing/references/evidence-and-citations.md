# Evidence And Citations

Use this reference before delivering a draft or revision.

## Citation Rules

- Only use citation keys returned by Syntara or provided by the user.
- Do not invent author-year markers, PMID values, DOI values, or cite keys.
- Keep `[@citekey]` markers inline unless the user requests another style.
- If a claim has no supporting source, either soften it or list it under "待补证据".
- Do not cite the user's manuscript or style corpus as literature unless the user explicitly says it is a citable source.
- Do not complete a full evidence-backed draft when the evidence ledger is empty. Return a provisional outline or evidence request instead.

## Evidence Ledger

Maintain a working ledger during drafting:

```text
Section:
Claim:
Evidence:
Cite keys:
Confidence:
Gap:
```

The ledger does not need to be shown unless the user asks, but it should guide the prose.

## Claim Checks

Before final output, scan for:

- comparative claims such as "better", "lower risk", "more predictable"
- numerical claims
- guideline-like recommendations
- causal claims
- statements about long-term prognosis
- claims that generalize from one indication to all patients

These usually need direct evidence.

If Syntara vector retrieval is not ready, verify these claims with full-text search and chunk context before drafting them.

## Style Checks

Do not let evidence handling turn the chapter into a literature review unless the user asked for that. A professional book chapter should usually explain clinical reasoning, then anchor key claims with citations.
