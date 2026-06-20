# Review And Revise Loop Design

## Goal

Syntara writing should treat the first draft as an intermediate artifact. For WorkBuddy, the loop must be enforceable without a full workflow state machine owned by Syntara.

## Chosen Approach

Use Skill rules plus a thin contract on the existing style-profile MCP tool.

- The Skill owns the writing sequence: source package, style package, argument plan, draft, style-aware review memo, revision plan, revised draft, final gate, human review, learning.
- `syntara_style_profile` provides a style-aware review packet so review cannot happen without the resolved style profile.
- `syntara_style_profile` allows learning only after human feedback or a human-edited final draft.

## MCP Boundary

Extend the existing `syntara_style_profile` tool with two actions:

- `prepare_review`: fetches the selected style profile, selects matching `style_exemplars`, and returns a review contract plus prompt-ready style package. It does not save anything.
- `learn_from_human_review`: forwards the original draft plus human feedback and/or human final text to the style-profile revision learner. It rejects AI-only review material.

## WorkBuddy Flow

WorkBuddy should call `syntara_style_profile` with `action: "prepare_review"` after a draft is produced and before revision. The model writes the review memo from that packet, then writes a revision plan, then revises. Only after the user comments or provides a final version should WorkBuddy call `syntara_style_profile` with `action: "learn_from_human_review"`.

## Boundaries

No new database tables, UI state, or workflow engine. Syntara does not try to own WorkBuddy conversation state. It only makes the critical gates explicit and callable.
