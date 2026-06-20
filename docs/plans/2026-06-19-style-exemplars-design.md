# Style Exemplars Design

## Goal

Syntara style profiles should preserve both abstract writing rules and a few concrete user-owned passages that can act as voice anchors during future writing. The current style profile is good at summarizing structure, tone, rhythm, and anti-AI rules, but it can lose the user's paragraph-level feel.

## Chosen Approach

Add a `style_exemplars` field to the existing style profile JSON instead of creating a new database table or API.

Each exemplar is a short user-owned excerpt with:

- `category`: passage role, such as `opening`, `judgment`, `mechanism`, `counterargument`, `tutorial`, `investment`, `product-note`, `ending`, or `revision-gold`.
- `use_when`: when a writing Skill should use it.
- `source_title`: the source document.
- `excerpt`: a short original passage, capped at 240 Chinese characters.
- `imitation_note`: what to imitate, such as judgment flow, sentence rhythm, explanation order, or paragraph breath.

## Data Flow

1. `syntara-style-profiler` reads the selected user-owned style corpus.
2. It extracts the normal Markdown + JSON profile.
3. It also selects 3-8 short style exemplars when the corpus supports them.
4. Writing Skills retrieve the profile as before.
5. Before outlining, they select 2-4 matching exemplars and use them as rhythm and author-position anchors.

## Boundaries

Style exemplars are not factual evidence and should not be quoted into a new draft by default. They are used to imitate cadence, judgment posture, explanation order, and paragraph breath. If no exemplar matches the task, the Skill uses the regular style profile rules.

This keeps the implementation small: no schema migration, no UI changes, and no new retrieval endpoint.
