# Common Writing Style Taxonomy

Use this taxonomy when choosing `writing_mode` and `style_type` for public Syntara style profiles.

## Source Basis

This taxonomy follows common public writing classifications instead of one user's private writing habits:

- Common Core writing standards use three broad text purposes: argument, informative/explanatory, and narrative.
- Traditional rhetorical modes commonly distinguish narration, description, exposition, and persuasion/argument.
- Professional and technical writing resources commonly organize genres by document form and audience need, such as memos, reports, proposals, white papers, documentation, instructions, presentations, and professional correspondence.
- Academic writing centers commonly list repeated student/professional genres such as abstracts, argument essays, literature reviews, proposals, presentations, summaries, reviews, and personal statements.

## Writing Mode

`writing_mode` describes the main purpose of the text. Use one of:

- `argument`: claims, critique, position-taking, recommendation, persuasion.
- `informative-explanatory`: explanation, instruction, reporting, analysis, synthesis.
- `narrative`: story, case, reflection, chronology, experience.
- `descriptive`: vivid description of a person, object, place, system, or state.
- `mixed`: substantial blending of several modes.

When unsure, choose the dominant reader task. A tutorial is usually `informative-explanatory`; an op-ed is usually `argument`; a case note may be `narrative`; a product page may be `mixed`.

## Style Type

`style_type` describes the reusable document genre or form. Prefer these generic values:

### Academic And Research

- `academic-paper`
- `abstract`
- `literature-review`
- `research-proposal`
- `annotated-bibliography`
- `review-critique`

### Professional And Technical

- `technical-report`
- `business-report`
- `white-paper`
- `proposal`
- `memo-email`
- `business-letter`
- `documentation`
- `instructional-guide`
- `manual`

### Public And Editorial

- `article`
- `blog-article`
- `op-ed`
- `review`
- `newsletter`
- `social-post`

### Presentation And Script

- `presentation`
- `talk-script`
- `course-script`

### Personal And Creative

- `personal-statement`
- `reflection`
- `creative-nonfiction`
- `narrative`

### Fallback

- `general`

## Use Public Values Directly

Do not create platform-specific or user-specific `style_type` values. Pick the closest public value above, and put narrower distinctions in `genre_matrix`, tags, or `style_exemplars.category`.
