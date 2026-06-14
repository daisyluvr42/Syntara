"""Project views backed by project:<slug> tags."""

from __future__ import annotations

import json
from collections import defaultdict

from fastapi import APIRouter

from backend.db.sqlite import get_connection, tag_filter_clause

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
async def list_projects():
    conn = get_connection()
    projects: dict[str, dict] = defaultdict(lambda: {"literature_count": 0, "corpus_count": 0})

    for table, key in (("literature", "literature_count"), ("corpus", "corpus_count")):
        rows = conn.execute(f"SELECT tags FROM {table}").fetchall()
        for row in rows:
            tags = json.loads(row["tags"]) if row["tags"] else []
            for tag in tags:
                if tag.startswith("project:"):
                    slug = tag.split(":", 1)[1]
                    projects[slug][key] += 1

    items = [
        {"slug": slug, **counts}
        for slug, counts in sorted(projects.items())
    ]
    return {"items": items, "total": len(items)}


@router.get("/{project}")
async def get_project(project: str):
    conn = get_connection()
    tag = f"project:{project}"
    literature_count = conn.execute(
        f"SELECT COUNT(*) as c FROM literature WHERE {tag_filter_clause()}",
        (tag,),
    ).fetchone()["c"]
    corpus_count = conn.execute(
        f"SELECT COUNT(*) as c FROM corpus WHERE {tag_filter_clause()}",
        (tag,),
    ).fetchone()["c"]
    return {
        "slug": project,
        "literature_count": literature_count,
        "corpus_count": corpus_count,
    }
