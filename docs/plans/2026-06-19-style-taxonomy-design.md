# Style Taxonomy Design

## Goal

Syntara needs public, reusable writing categories that work for many users. The taxonomy should not be based on one user's topics or platforms.

## Source Basis

The taxonomy combines common writing-purpose categories with common academic, professional, and public writing genres:

- broad purpose: argument, informative/explanatory, narrative, descriptive, or mixed;
- document genre: academic paper, literature review, proposal, report, memo/email, documentation, instructional guide, article, presentation, social post, and similar public forms.

## Chosen Shape

Use two fields:

- `writing_mode`: the broad purpose of the text.
- `style_type`: the reusable document genre.

Topic- or user-specific distinctions should not become `style_type` values. Put them in tags, `genre_matrix`, or `style_exemplars.category`.

## Use Current Taxonomy Only

This taxonomy is new and should be used directly. Existing draft labels should be updated to the generic values in `skills/syntara-style-profiler/references/style-taxonomy.md`.
