# Syntara Style Profile JSON Schema

Use this shape for `profile_json` when calling `syntara_style_profile` with `action: "save"`.

```json
{
  "schema": "syntara.style_profile.v1",
  "name": "公众号长文风格",
  "project": "default",
  "style_type": "wechat-longform",
  "source": {
    "kind": "local-folder",
    "path_or_id": "/absolute/path/to/corpus",
    "source_count": 0,
    "source_titles": [],
    "excluded_sources": [
      {
        "path_or_id": "",
        "reason": ""
      }
    ],
    "sample_strategy": "all-files"
  },
  "updated_from_profile_id": null,
  "tone": {
    "summary": "",
    "do": [],
    "avoid": []
  },
  "writer_profile": {
    "summary": "",
    "voice_origin": [],
    "do_not_assume": []
  },
  "tone_spectrum": [
    {
      "context": "",
      "tone": "",
      "use_when": "",
      "avoid_when": ""
    }
  ],
  "structure": {
    "opening_patterns": [],
    "section_patterns": [],
    "ending_patterns": []
  },
  "rhythm": {
    "paragraphs": "",
    "sentences": "",
    "transitions": []
  },
  "argumentation": {
    "claim_style": "",
    "evidence_style": "",
    "counterargument_style": ""
  },
  "reader_relationship": {
    "person_strategy": "",
    "expectation_management": [],
    "epistemic_honesty": []
  },
  "lexicon": {
    "prefer": [],
    "avoid": [],
    "english_usage": "",
    "caution": []
  },
  "formatting": {
    "headings": "",
    "lists": "",
    "bold": "",
    "images": ""
  },
  "anti_ai": {
    "banned_moves": [],
    "final_checklist": []
  },
  "evidence": [
    {
      "rule": "",
      "source_title": "",
      "example": "",
      "note": ""
    }
  ],
  "genre_matrix": {},
  "cross_genre_constants": [],
  "style_evolution": {
    "periods": [],
    "current_priority": "",
    "deprecated_habits": []
  },
  "revision_preferences": [
    {
      "summary": "",
      "learned_at": "",
      "base_profile_id": "",
      "do": [],
      "avoid": [],
      "sentence_level": [],
      "structure_level": [],
      "diction_level": [],
      "evidence_level": [],
      "formatting_level": [],
      "over_polish_patterns": [],
      "examples": [
        {
          "before": "",
          "after": "",
          "preference": ""
        }
      ]
    }
  ],
  "genre_variants": {},
  "confidence": {
    "level": "medium",
    "notes": ""
  }
}
```

Rules:

- Keep arrays short and operational.
- Put examples and nuance in `profile_markdown`.
- `source_count` must reflect the actual number of source documents read or analyzed.
- `source.source_titles` must contain only documents actually included from the user-resolved corpus.
- When the user provided an explicit path or file list, `source.path_or_id` is the boundary; do not include evidence from outside that boundary.
- `source.excluded_sources` records files or folders intentionally skipped because the user requested it or a corpus manifest/readme marked them as excluded.
- `updated_from_profile_id` should be the prior Syntara profile id when updating a profile.
- `evidence` should contain short examples or tight paraphrases tied to filenames. It is not a quote dump; it exists to prevent unsupported style claims.
- `tone_spectrum`, `genre_matrix`, `reader_relationship`, and `style_evolution` are required when the corpus has mixed genres or spans a meaningful time period.
- `revision_preferences` stores durable user editing habits learned from original/revised draft pairs. Keep examples short and merge them into the same profile instead of creating a separate diff profile. Use `over_polish_patterns` for AI-like revisions the user tends to undo, such as meaning inflation, forced contrast, invented scene detail, excessive smoothing, or loss of colloquial rhythm.
- Use `confidence.level` as `low`, `medium`, or `high`.
