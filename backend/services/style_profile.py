"""Build and store reusable writing style profiles."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from backend.config import STYLES_DIR
from backend.db.sqlite import get_connection, tag_filter_clause
from backend.services.extract_cache import load_cached
from backend.services.ai_provider import chat_completion


MAX_STYLE_CORPUS_CHARS = 60000
PROFILE_MAX_TOKENS = 8192
PROFILE_REQUIRED_KEYS = [
    "source",
    "writing_mode",
    "writer_profile",
    "tone",
    "tone_spectrum",
    "structure",
    "rhythm",
    "argumentation",
    "reader_relationship",
    "lexicon",
    "formatting",
    "anti_ai",
    "style_exemplars",
    "evidence",
    "genre_matrix",
    "cross_genre_constants",
    "style_evolution",
    "revision_workflow",
    "confidence",
    "reusable_markdown_profile",
]


async def build_style_profile(
    name: str,
    project: str = "default",
    style_type: str | None = None,
    corpus_ids: list[str] | None = None,
    tag: str | None = None,
    content: str | None = None,
    source_title: str | None = None,
    provider_id: str | None = None,
    set_default: bool = True,
) -> dict:
    style_type = _slug(style_type) if style_type else None
    source_texts, source_ids, source_titles = _collect_style_sources(corpus_ids or [], tag, content, source_title)
    combined = _prepare_style_corpus(source_texts)
    if not combined.strip():
        raise ValueError("No style corpus content found")

    source_label = source_title or (f"tag:{tag}" if tag else ",".join(source_ids) or "direct style corpus")
    profile_json = await _extract_profile_json(
        name,
        project,
        combined,
        provider_id,
        style_type,
        source_label,
        source_titles,
    )
    profile_markdown = _profile_to_markdown(profile_json)

    return save_style_profile(
        name=name,
        project=project,
        style_type=style_type,
        profile_json=profile_json,
        profile_markdown=profile_markdown,
        source_corpus_ids=source_ids,
        tags=[],
        set_default=set_default,
    )


async def update_style_profile_from_revision(
    original_text: str,
    revised_text: str | None = None,
    human_feedback: str | None = None,
    base_profile_id: str | None = None,
    name: str | None = None,
    project: str = "default",
    style_type: str | None = None,
    source_title: str | None = None,
    provider_id: str | None = None,
    set_default: bool = True,
) -> dict:
    style_type = _slug(style_type) if style_type else None
    if not original_text.strip():
        raise ValueError("original_text is required")
    if not (revised_text or "").strip() and not (human_feedback or "").strip():
        raise ValueError("human revised text or human feedback is required")

    base_profile = _get_base_profile(base_profile_id, project)
    profile_name = name or (base_profile["name"] if base_profile else "Revision-learned style profile")
    profile_project = base_profile["project"] if base_profile else project
    profile_style_type = style_type or (base_profile.get("style_type") if base_profile else None)

    revision = await _extract_revision_preferences(
        original_text=_trim_corpus(original_text),
        revised_text=_trim_corpus(revised_text or ""),
        human_feedback=_trim_corpus(human_feedback or ""),
        base_profile=base_profile,
        source_title=source_title,
        provider_id=provider_id,
    )
    profile_json = _merge_revision_into_profile(
        base_profile["profile_json"] if base_profile else {},
        revision,
        profile_name,
        profile_project,
        profile_style_type,
        base_profile["id"] if base_profile else None,
    )
    profile_markdown = _merge_revision_markdown(
        base_profile["profile_markdown"] if base_profile else f"# {profile_name}",
        revision,
        source_title,
        base_profile["id"] if base_profile else None,
    )

    return save_style_profile(
        name=profile_name,
        project=profile_project,
        style_type=profile_style_type,
        profile_json=profile_json,
        profile_markdown=profile_markdown,
        source_corpus_ids=base_profile["source_corpus_ids"] if base_profile else [],
        tags=["revision-learned"],
        set_default=set_default,
    )


def save_style_profile(
    name: str,
    project: str = "default",
    style_type: str | None = None,
    profile_json: dict | None = None,
    profile_markdown: str = "",
    source_corpus_ids: list[str] | None = None,
    tags: list[str] | None = None,
    set_default: bool = True,
) -> dict:
    if not profile_markdown.strip():
        raise ValueError("profile_markdown is required")

    profile_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    profile_json = profile_json or {}
    style_type = _slug(style_type) if style_type else None
    if style_type:
        profile_json["style_type"] = style_type

    final_tags = ["style-profile", f"project:{project}"]
    if style_type:
        final_tags.append(f"style-type:{_slug(style_type)}")
    for tag in tags or []:
        if tag not in final_tags:
            final_tags.append(tag)
    conn = get_connection()

    if set_default:
        conn.execute("UPDATE style_profile SET is_default = 0 WHERE project = ?", (project,))

    conn.execute(
        """
        INSERT INTO style_profile (
            id, name, project, profile_json, profile_markdown, source_corpus_ids,
            tags, is_default, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            profile_id,
            name,
            project,
            json.dumps(profile_json, ensure_ascii=False),
            profile_markdown,
            json.dumps(source_corpus_ids or [], ensure_ascii=False),
            json.dumps(final_tags, ensure_ascii=False),
            int(set_default),
            now,
            now,
        ),
    )
    conn.commit()
    _write_profile_files(profile_id, name, project, profile_json, profile_markdown)
    return get_style_profile(profile_id=profile_id)


def _get_base_profile(base_profile_id: str | None, project: str) -> dict | None:
    if base_profile_id:
        return get_style_profile(profile_id=base_profile_id)
    try:
        return get_style_profile(project=project, default=True)
    except ValueError:
        return None


def list_style_profiles(project: str | None = None, style_type: str | None = None) -> dict:
    conn = get_connection()
    params: list = []
    query = "SELECT id, name, project, tags, is_default, created_at, updated_at FROM style_profile"
    where = []
    if project:
        where.append("project = ?")
        params.append(project)
    if style_type:
        where.append(tag_filter_clause())
        params.append(f"style-type:{_slug(style_type)}")
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY is_default DESC, updated_at DESC"
    rows = conn.execute(query, params).fetchall()
    return {"items": [_summary_from_row(row) for row in rows], "total": len(rows)}


def get_style_profile(
    profile_id: str | None = None,
    project: str | None = None,
    name: str | None = None,
    default: bool = False,
) -> dict:
    conn = get_connection()
    if profile_id:
        row = conn.execute("SELECT * FROM style_profile WHERE id = ?", (profile_id,)).fetchone()
    elif default:
        row = conn.execute(
            "SELECT * FROM style_profile WHERE project = ? AND is_default = 1 ORDER BY updated_at DESC LIMIT 1",
            (project or "default",),
        ).fetchone()
    elif project and name:
        row = conn.execute(
            "SELECT * FROM style_profile WHERE project = ? AND name = ? ORDER BY updated_at DESC LIMIT 1",
            (project, name),
        ).fetchone()
    else:
        row = None
    if not row:
        raise ValueError("Style profile not found")
    return _profile_from_row(row)


def set_default_style_profile(profile_id: str | None = None, project: str | None = None, name: str | None = None) -> dict:
    profile = get_style_profile(profile_id=profile_id, project=project, name=name)
    conn = get_connection()
    conn.execute("UPDATE style_profile SET is_default = 0 WHERE project = ?", (profile["project"],))
    conn.execute(
        "UPDATE style_profile SET is_default = 1, updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), profile["id"]),
    )
    conn.commit()
    return get_style_profile(profile_id=profile["id"])


def _collect_style_sources(
    corpus_ids: list[str],
    tag: str | None,
    content: str | None,
    source_title: str | None,
) -> tuple[list[str], list[str], list[str]]:
    texts = []
    source_ids = []
    source_titles = []
    if content:
        title = source_title or "direct style corpus"
        texts.append(f"# {title}\n\n{content}")
        source_titles.append(title)

    conn = get_connection()
    rows = []
    if corpus_ids:
        placeholders = ",".join("?" for _ in corpus_ids)
        rows.extend(conn.execute(f"SELECT * FROM corpus WHERE id IN ({placeholders})", corpus_ids).fetchall())
    if tag:
        rows.extend(conn.execute(f"SELECT * FROM corpus WHERE {tag_filter_clause()}", (tag,)).fetchall())

    seen = set()
    for row in rows:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        text = _read_corpus_text(row)
        if text.strip():
            texts.append(f"# {row['title']}\n\n{text}")
            source_ids.append(row["id"])
            source_titles.append(row["title"])
    return texts, source_ids, source_titles


def _read_corpus_text(row) -> str:
    if row["file_type"] == "pdf":
        cached = load_cached(row["file_hash"])
        if cached:
            return "\n\n".join(str(el.get("content", "")) for el in cached)
        return ""

    path = Path(row["file_path"])
    if path.exists():
        return path.read_text(encoding="utf-8", errors="ignore")
    return ""


async def _extract_profile_json(
    name: str,
    project: str,
    corpus: str,
    provider_id: str | None,
    style_type: str | None,
    source_label: str,
    source_titles: list[str],
) -> dict:
    source_titles_json = json.dumps(source_titles, ensure_ascii=False, indent=2)
    example_shape = """
{
  "schema": "syntara.style_profile.v1",
  "name": "示例风格",
  "project": "default",
  "style_type": "blog-article",
  "writing_mode": "argument",
  "source": {"path_or_id": "示例语料", "source_count": 2, "source_titles": ["A.md"], "excluded_sources": [], "sample_strategy": "mcp-build"},
  "writer_profile": {"summary": "机制型解释者", "voice_origin": ["行业经验"], "do_not_assume": []},
  "tone": {"summary": "克制、判断明确"},
  "tone_spectrum": [{"context": "教程", "tone": "直接可操作", "use_when": "解释步骤", "avoid_when": "需要文学化表达"}],
  "structure": {"opening_patterns": [{"pattern": "问题切入", "use_for": ["教程"], "example": "先问一个问题", "source": "A.md"}], "section_patterns": [], "ending_patterns": []},
  "rhythm": {"sentence": "长句解释，短句收束", "paragraph": "短段推进"},
  "argumentation": {"claim_style": "先框架后判断", "evidence_style": "证据服务机制", "counterargument_style": "预设反驳"},
  "reader_relationship": {"person_strategy": "少量第二人称", "expectation_management": [], "epistemic_honesty": []},
  "lexicon": {"prefer": [], "avoid": [], "english_usage": "", "caution": []},
  "formatting": {"headings": "", "bold": "", "tables": "", "quotes": ""},
  "anti_ai": {"banned_moves": [], "final_checklist": []},
  "style_exemplars": [
    {
      "category": "judgment",
      "use_when": "需要先给判断再解释",
      "source_title": "A.md",
      "excerpt": "不超过 240 个中文字符的原文短摘录",
      "imitation_note": "模仿判断推进和句子节奏，不复制内容"
    }
  ],
  "evidence": [{"rule": "先框架后判断", "source_title": "A.md", "example": "短例或转述", "note": "why it matters"}],
  "genre_matrix": {"教程": {"opening": "", "structure": "", "evidence": "", "person": "", "ending": "", "tone": ""}},
  "cross_genre_constants": [],
  "style_evolution": {"periods": [], "current_priority": "", "deprecated_habits": []},
  "revision_workflow": {"do": [], "avoid": []},
  "confidence": {"level": "medium", "notes": []},
  "reusable_markdown_profile": "# 示例风格\\n..."
}
""".strip()
    prompt = f"""
You extract reusable Chinese writing style profiles for Syntara.
Return strict JSON only. No markdown fence.

Profile name: {name}
Project: {project}
Style type: {style_type or "auto"}
Source label: {source_label or "direct style corpus"}
Source titles:
{source_titles_json}

The JSON object must follow `syntara.style_profile.v1` and use these practical keys:
- schema
- name
- project
- style_type
- writing_mode
- source: object with path_or_id, source_count, source_titles, excluded_sources, sample_strategy
- writer_profile
- tone
- tone_spectrum
- structure
- rhythm
- argumentation
- reader_relationship
- lexicon
- formatting
- anti_ai
- style_exemplars
- evidence
- genre_matrix
- cross_genre_constants
- style_evolution
- revision_workflow
- confidence
- reusable_markdown_profile

ALL keys above are required. Do not omit a key. If evidence is thin, use the field's zero value and explain the limitation in confidence.notes.

Example shape:
{example_shape}

Write `reusable_markdown_profile` in Chinese, shaped like a compact style document a writing Skill can follow.
Do not copy long source passages. Extract habits, rules, and constraints.
Use common public taxonomy for classification. `writing_mode` must be one of argument, informative-explanatory, narrative, descriptive, or mixed. Prefer generic `style_type` values such as academic-paper, abstract, literature-review, research-proposal, review-critique, technical-report, business-report, white-paper, proposal, memo-email, business-letter, documentation, instructional-guide, manual, article, blog-article, op-ed, review, newsletter, social-post, presentation, talk-script, course-script, personal-statement, reflection, creative-nonfiction, narrative, or general.
Avoid user-specific style_type values. Put narrower topical distinctions in genre_matrix, tags, evidence, or style_exemplars.category.
Also extract 3-8 `style_exemplars` when the corpus supports them. Each exemplar must be a short original user-owned excerpt, no more than 240 Chinese characters, tagged with one category such as opening, judgment, mechanism, transition, counterargument, tutorial, investment, product-note, ending, or revision-gold.
Use `style_exemplars` as rhythm and judgment anchors for future writing, not as quotable content.
Tie important claims to short examples or tight paraphrases in `evidence`.
Distinguish "appears in corpus" from "recommended to imitate".
Do not include source titles outside the provided source list.

Style corpus:
{corpus}
""".strip()
    raw = await chat_completion(
        provider_id,
        [{"role": "user", "content": prompt}],
        max_tokens=PROFILE_MAX_TOKENS,
        temperature=0.2,
    )
    data = _parse_json_object(raw)
    data.setdefault("schema", "syntara.style_profile.v1")
    data.setdefault("name", name)
    data.setdefault("project", project)
    if style_type:
        data.setdefault("style_type", style_type)
    source = data.setdefault("source", {})
    if isinstance(source, dict):
        source["path_or_id"] = source_label
        source["source_count"] = len(source_titles)
        source["source_titles"] = source_titles
        source.setdefault("excluded_sources", [])
        source.setdefault("sample_strategy", "mcp-build")
    _normalize_profile_shape(data)
    return data


async def _extract_revision_preferences(
    original_text: str,
    revised_text: str,
    human_feedback: str,
    base_profile: dict | None,
    source_title: str | None,
    provider_id: str | None,
) -> dict:
    base_json = json.dumps(base_profile["profile_json"], ensure_ascii=False, indent=2) if base_profile else "{}"
    base_markdown = base_profile["profile_markdown"] if base_profile else ""
    prompt = f"""
You update a reusable Syntara Chinese writing style profile from a user's revision.
Compare ORIGINAL DRAFT with USER REVISED VERSION and/or USER FEEDBACK. Infer only durable user editing preferences.
Return strict JSON only. No markdown fence.

Source title: {source_title or "revision pair"}
Existing profile JSON:
{base_json}

Existing profile Markdown:
{base_markdown[:12000]}

Required JSON keys:
- revision_summary: concise Chinese summary of what the user changed.
- profile_json_patch: partial JSON to merge into the existing Syntara style profile. Use existing schema keys where possible, especially tone, tone_spectrum, structure, rhythm, argumentation, reader_relationship, lexicon, formatting, anti_ai, style_exemplars, evidence, genre_matrix, style_evolution, revision_workflow.
- revision_preferences: object with do, avoid, sentence_level, structure_level, diction_level, evidence_level, formatting_level, examples.
- reusable_markdown_addendum: Chinese Markdown section to append to the existing profile. It must be directly usable as writing instructions.

Rules:
- Learn only from human-provided material. Do not infer preferences from an AI self-review, AI revision plan, or AI-generated second draft.
- Treat factual additions as evidence discipline only, not as style facts.
- Do not copy long passages. Examples must be short before/after snippets.
- If the user's revised version contains a strong reusable voice anchor, add a short `revision-gold` item to profile_json_patch.style_exemplars. Keep the excerpt under 240 Chinese characters.
- If only user feedback is provided and no user revised text exists, do not add `revision-gold`; update revision preferences and anti_ai/style rules only.
- Focus on user choices: what they deleted, compressed, expanded, reordered, renamed, softened, sharpened, or made more concrete.
- If the difference is small, say confidence is low in revision_preferences.

ORIGINAL DRAFT:
{original_text}

USER REVISED VERSION:
{revised_text or "(not provided)"}

USER FEEDBACK:
{human_feedback or "(not provided)"}
""".strip()
    raw = await chat_completion(
        provider_id,
        [{"role": "user", "content": prompt}],
        max_tokens=PROFILE_MAX_TOKENS,
        temperature=0.2,
    )
    data = _parse_json_object(raw)
    data.setdefault("revision_summary", "")
    data.setdefault("profile_json_patch", {})
    data.setdefault("revision_preferences", {})
    data.setdefault("reusable_markdown_addendum", "")
    return data


def _merge_revision_into_profile(
    base_json: dict,
    revision: dict,
    name: str,
    project: str,
    style_type: str | None,
    base_profile_id: str | None,
) -> dict:
    merged = json.loads(json.dumps(base_json or {}, ensure_ascii=False))
    merged.setdefault("schema", "syntara.style_profile.v1")
    merged["name"] = name
    merged["project"] = project
    if style_type:
        merged["style_type"] = style_type
    merged["updated_from_profile_id"] = base_profile_id
    _deep_merge(merged, revision.get("profile_json_patch") or {})

    revision_item = revision.get("revision_preferences") or {}
    revision_item.setdefault("summary", revision.get("revision_summary", ""))
    revision_item.setdefault("learned_at", datetime.now().isoformat())
    if base_profile_id:
        revision_item.setdefault("base_profile_id", base_profile_id)
    preferences = merged.setdefault("revision_preferences", [])
    if not isinstance(preferences, list):
        preferences = [preferences]
        merged["revision_preferences"] = preferences
    preferences.append(revision_item)
    merged["reusable_markdown_profile"] = _merge_revision_markdown(
        str(merged.get("reusable_markdown_profile") or ""),
        revision,
        None,
        base_profile_id,
    ).strip()
    _normalize_profile_shape(merged)
    return merged


def _merge_revision_markdown(
    base_markdown: str,
    revision: dict,
    source_title: str | None,
    base_profile_id: str | None,
) -> str:
    addendum = str(revision.get("reusable_markdown_addendum") or "").strip()
    if not addendum:
        prefs = revision.get("revision_preferences") or {}
        addendum_lines = ["## Revision Preferences From User Edits", ""]
        summary = revision.get("revision_summary") or prefs.get("summary")
        if summary:
            addendum_lines.extend([str(summary), ""])
        for label, key in (("Do", "do"), ("Avoid", "avoid")):
            values = prefs.get(key) or []
            if values:
                addendum_lines.append(f"### {label}")
                addendum_lines.extend(f"- {item}" for item in values)
                addendum_lines.append("")
        addendum = "\n".join(addendum_lines).strip()

    header = ["", "## Revision Preferences From User Edits", ""]
    if source_title:
        header.append(f"> Source revision: {source_title}.")
    if base_profile_id:
        header.append(f"> Updated from profile: `{base_profile_id}`.")
    header.append(f"> Learned at: {datetime.now().isoformat()}.")
    header.append("")
    if addendum.startswith("## Revision Preferences From User Edits"):
        return f"{base_markdown.rstrip()}\n\n{addendum}".strip()
    return f"{base_markdown.rstrip()}\n{chr(10).join(header)}{addendum}".strip()


def _deep_merge(target: dict, patch: dict) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        elif isinstance(value, list) and isinstance(target.get(key), list):
            target[key] = _unique_list(target[key] + value)
        elif value not in (None, "", [], {}):
            target[key] = value


def _unique_list(values: list) -> list:
    seen = set()
    result = []
    for value in values:
        marker = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(value)
    return result


def _normalize_profile_shape(profile: dict) -> None:
    missing = []
    empty = []
    for key in PROFILE_REQUIRED_KEYS:
        if key not in profile:
            profile[key] = _zero_value_for_profile_key(key)
            missing.append(key)
        elif profile[key] in ("", [], {}):
            empty.append(key)

    confidence = profile.setdefault("confidence", {})
    if not isinstance(confidence, dict):
        confidence = {"level": str(confidence), "notes": []}
        profile["confidence"] = confidence
    confidence.setdefault("level", "medium")
    notes = confidence.setdefault("notes", [])
    if missing:
        notes.append(f"Missing required fields filled with zero values: {', '.join(missing)}")
    if empty:
        notes.append(f"Required fields were empty and may need better corpus evidence: {', '.join(empty)}")


def _zero_value_for_profile_key(key: str):
    if key == "source":
        return {"path_or_id": "", "source_count": 0, "source_titles": [], "excluded_sources": [], "sample_strategy": ""}
    if key == "writing_mode":
        return "mixed"
    if key == "writer_profile":
        return {"summary": "", "voice_origin": [], "do_not_assume": []}
    if key == "tone":
        return {"summary": ""}
    if key == "structure":
        return {"opening_patterns": [], "section_patterns": [], "ending_patterns": []}
    if key == "rhythm":
        return {"sentence": "", "paragraph": ""}
    if key == "argumentation":
        return {"claim_style": "", "evidence_style": "", "counterargument_style": ""}
    if key == "reader_relationship":
        return {"person_strategy": "", "expectation_management": [], "epistemic_honesty": []}
    if key == "lexicon":
        return {"prefer": [], "avoid": [], "english_usage": "", "caution": []}
    if key == "formatting":
        return {"headings": "", "bold": "", "tables": "", "quotes": ""}
    if key == "anti_ai":
        return {"banned_moves": [], "final_checklist": []}
    if key == "style_exemplars":
        return []
    if key == "style_evolution":
        return {"periods": [], "current_priority": "", "deprecated_habits": []}
    if key == "revision_workflow":
        return {"do": [], "avoid": []}
    if key == "confidence":
        return {"level": "medium", "notes": []}
    if key == "reusable_markdown_profile":
        return ""
    if key == "genre_matrix":
        return {}
    return []


def _parse_json_object(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.S)
        if match:
            return json.loads(match.group(0))
        raise


def _profile_to_markdown(profile: dict) -> str:
    if profile.get("reusable_markdown_profile"):
        return str(profile["reusable_markdown_profile"]).strip()
    lines = [f"# {profile.get('name', 'Style Profile')}", ""]
    for key, value in profile.items():
        if key in {"name", "project"}:
            continue
        title = key.replace("_", " ").title()
        lines.append(f"## {title}")
        if isinstance(value, list):
            lines.extend(f"- {item}" for item in value)
        else:
            lines.append(str(value))
        lines.append("")
    return "\n".join(lines).strip()


def _write_profile_files(profile_id: str, name: str, project: str, profile_json: dict, profile_markdown: str) -> None:
    project_dir = STYLES_DIR / _safe_filename(project)
    project_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{_safe_filename(name)}-{profile_id[:8]}"
    (project_dir / f"{stem}.json").write_text(json.dumps(profile_json, ensure_ascii=False, indent=2), encoding="utf-8")
    (project_dir / f"{stem}.md").write_text(profile_markdown, encoding="utf-8")


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", value, flags=re.UNICODE).strip("._")
    return cleaned[:80] or "style"


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip()).strip("-").lower() or "general"


def _prepare_style_corpus(source_texts: list[str]) -> str:
    total = sum(len(text) for text in source_texts)
    if total <= MAX_STYLE_CORPUS_CHARS:
        return "\n\n---\n\n".join(source_texts)

    quota = max(1, MAX_STYLE_CORPUS_CHARS // max(len(source_texts), 1))
    samples = []
    for text in source_texts:
        if len(text) <= quota:
            samples.append(text)
            continue
        head_len = max(1, quota * 2 // 3)
        tail_len = max(1, quota - head_len)
        samples.append(f"{text[:head_len]}\n\n[...source sample trimmed...]\n\n{text[-tail_len:]}")
    return "\n\n---\n\n".join(samples)


def _trim_corpus(text: str) -> str:
    if len(text) <= MAX_STYLE_CORPUS_CHARS:
        return text
    head = text[: MAX_STYLE_CORPUS_CHARS // 2]
    tail = text[-MAX_STYLE_CORPUS_CHARS // 2 :]
    return f"{head}\n\n[...style corpus trimmed...]\n\n{tail}"


def _summary_from_row(row) -> dict:
    item = dict(row)
    item["tags"] = json.loads(item["tags"] or "[]")
    item["style_type"] = _style_type_from_tags(item["tags"])
    item["is_default"] = bool(item["is_default"])
    return item


def _profile_from_row(row) -> dict:
    item = dict(row)
    item["profile_json"] = json.loads(item["profile_json"] or "{}")
    _normalize_profile_shape(item["profile_json"])
    item["style_type"] = item["profile_json"].get("style_type") or _style_type_from_tags(json.loads(item["tags"] or "[]"))
    item["source_corpus_ids"] = json.loads(item["source_corpus_ids"] or "[]")
    item["tags"] = json.loads(item["tags"] or "[]")
    item["is_default"] = bool(item["is_default"])
    return item


def _style_type_from_tags(tags: list[str]) -> str | None:
    for tag in tags:
        if tag.startswith("style-type:"):
            return tag.split(":", 1)[1]
    return None
