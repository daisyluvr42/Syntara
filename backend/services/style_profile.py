"""Build and store reusable writing style profiles."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from backend.config import STYLES_DIR
from backend.db.sqlite import get_connection
from backend.services.extract_cache import load_cached
from backend.services.ai_provider import chat_completion


MAX_STYLE_CORPUS_CHARS = 60000


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
    source_texts, source_ids = _collect_style_sources(corpus_ids or [], tag, content, source_title)
    combined = _trim_corpus("\n\n---\n\n".join(source_texts))
    if not combined.strip():
        raise ValueError("No style corpus content found")

    profile_json = await _extract_profile_json(name, project, combined, provider_id, style_type)
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
    if style_type:
        profile_json.setdefault("style_type", style_type)

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


def list_style_profiles(project: str | None = None, style_type: str | None = None) -> dict:
    conn = get_connection()
    params: list = []
    query = "SELECT id, name, project, tags, is_default, created_at, updated_at FROM style_profile"
    where = []
    if project:
        where.append("project = ?")
        params.append(project)
    if style_type:
        where.append("tags LIKE ?")
        params.append(f"%style-type:{_slug(style_type)}%")
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
) -> tuple[list[str], list[str]]:
    texts = []
    source_ids = []
    if content:
        title = source_title or "direct style corpus"
        texts.append(f"# {title}\n\n{content}")

    conn = get_connection()
    rows = []
    if corpus_ids:
        placeholders = ",".join("?" for _ in corpus_ids)
        rows.extend(conn.execute(f"SELECT * FROM corpus WHERE id IN ({placeholders})", corpus_ids).fetchall())
    if tag:
        rows.extend(conn.execute("SELECT * FROM corpus WHERE tags LIKE ?", (f"%{tag}%",)).fetchall())

    seen = set()
    for row in rows:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        text = _read_corpus_text(row)
        if text.strip():
            texts.append(f"# {row['title']}\n\n{text}")
            source_ids.append(row["id"])
    return texts, source_ids


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
) -> dict:
    prompt = f"""
You extract reusable Chinese writing style profiles for Syntara.
Return strict JSON only. No markdown fence.

Profile name: {name}
Project: {project}
Style type: {style_type or "auto"}

The JSON object must use these keys:
- name
- project
- style_type
- audience_and_tone
- argument_style
- structure_and_rhythm
- sentence_and_paragraph_rules
- rhetoric_devices
- terminology_rules
- evidence_and_caveats
- do
- avoid
- reusable_markdown_profile

Write `reusable_markdown_profile` in Chinese, shaped like a compact style document a writing Skill can follow.
Do not copy long source passages. Extract habits, rules, and constraints.

Style corpus:
{corpus}
""".strip()
    raw = await chat_completion(
        provider_id,
        [{"role": "user", "content": prompt}],
        max_tokens=4096,
        temperature=0.2,
    )
    data = _parse_json_object(raw)
    data.setdefault("name", name)
    data.setdefault("project", project)
    if style_type:
        data.setdefault("style_type", style_type)
    return data


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
