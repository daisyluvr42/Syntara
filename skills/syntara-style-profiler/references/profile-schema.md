# Syntara Style Profile JSON Schema

Use this shape for `profile_json` when calling `syntara_save_style_profile`.

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
    "sample_strategy": "all-files"
  },
  "updated_from_profile_id": null,
  "tone": {
    "summary": "",
    "do": [],
    "avoid": []
  },
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
  "lexicon": {
    "prefer": [],
    "avoid": [],
    "english_usage": ""
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
- `updated_from_profile_id` should be the prior Syntara profile id when updating a profile.
- Use `confidence.level` as `low`, `medium`, or `high`.
