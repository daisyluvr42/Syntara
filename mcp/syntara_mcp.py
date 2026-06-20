#!/usr/bin/env python3
"""Minimal MCP stdio bridge for Syntara."""

from __future__ import annotations

import asyncio
import atexit
import json
import os
import re
import subprocess
import sys
from typing import Any
from pathlib import Path
from urllib.parse import urlparse

import httpx

BASE_URL = os.getenv("SYNTARA_BASE_URL", "http://127.0.0.1:8888").rstrip("/")
TIMEOUT = float(os.getenv("SYNTARA_MCP_TIMEOUT", "60"))
STYLE_TIMEOUT = float(os.getenv("SYNTARA_MCP_STYLE_TIMEOUT", "180"))
AUTO_START = os.getenv("SYNTARA_MCP_AUTO_START", "1") != "0"
IDLE_SECONDS = float(os.getenv("SYNTARA_MCP_IDLE_SECONDS", "3600"))
BASE_DIR = Path(__file__).resolve().parents[1]
BACKEND_PROCESS: asyncio.subprocess.Process | None = None
BACKEND_LOG_FILE: Any | None = None
BACKEND_STARTED_BY_MCP = False
BACKEND_ATEXIT_REGISTERED = False
HTTP_CLIENT: httpx.AsyncClient | None = None
IDLE_TASK: asyncio.Task | None = None
ACTIVE_REQUESTS = 0
LAST_BACKEND_USED_AT = 0.0
MESSAGE_MODE = "headers"
SUPPORTED_PROTOCOL_VERSION = "2024-11-05"


AGGREGATE_TOOLS: list[dict[str, Any]] = [
    {
        "name": "syntara_status",
        "description": "Check Syntara health and project status. Use action health, list_projects, or project_summary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["health", "list_projects", "project_summary"], "default": "health"},
                "project": {"type": "string", "description": "Required for project_summary."},
            },
        },
    },
    {
        "name": "syntara_retrieve",
        "description": "Retrieve evidence from Syntara. Use for search, RAG answers, grouped literature search, or chunk context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["search", "rag_answer", "literature_grouped", "chunk_context"], "default": "search"},
                "query": {"type": "string", "description": "Search query for search mode."},
                "question": {"type": "string", "description": "Bounded question for rag_answer mode."},
                "scope": {"type": "string", "enum": ["all", "literature", "corpus"], "default": "all"},
                "search_scope": {"type": "string", "enum": ["all", "literature", "corpus"], "default": "all"},
                "zh_query": {"type": "string", "description": "Chinese query for literature_grouped mode."},
                "en_query": {"type": "string", "description": "English query for literature_grouped mode."},
                "lit_id": {"type": "string", "description": "Literature id for chunk_context mode."},
                "chunk_index": {"type": "integer", "description": "Chunk index for chunk_context mode."},
                "top_k": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                "use_tree": {"type": "boolean", "default": True},
                "provider_id": {"type": "string"},
                "project": {"type": "string"},
            },
        },
    },
    {
        "name": "syntara_sources",
        "description": "List Syntara source inventory. Use source_type literature or corpus.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_type": {"type": "string", "enum": ["literature", "corpus"], "default": "literature"},
                "skip": {"type": "integer", "default": 0, "minimum": 0},
                "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
                "tag": {"type": "string"},
                "sort_by": {"type": "string", "enum": ["title", "year", "created_at", "updated_at", "imported_at", "cite_key"], "default": "updated_at"},
                "order": {"type": "string", "enum": ["asc", "desc"], "default": "desc"},
                "project": {"type": "string"},
            },
        },
    },
    {
        "name": "syntara_import",
        "description": "Import sources into Syntara. Use source_type corpus_text, literature_pdfs, or pubmed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_type": {"type": "string", "enum": ["corpus_text", "literature_pdfs", "pubmed"]},
                "title": {"type": "string"},
                "content": {"type": "string"},
                "description": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "source_url": {"type": "string"},
                "source_id": {"type": "string"},
                "file_paths": {"type": "array", "items": {"type": "string"}},
                "folder_path": {"type": "string"},
                "recursive": {"type": "boolean", "default": False},
                "pmids": {"type": "array", "items": {"type": "string"}},
                "project": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["source_type"],
        },
    },
    {
        "name": "syntara_style_profile",
        "description": "List, get, build, save, update, or set default Syntara style profiles.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "get", "build", "save", "update", "update_from_revision", "prepare_review", "learn_from_human_review", "set_default"]},
                "name": {"type": "string"},
                "project": {"type": "string", "default": "default"},
                "style_type": {"type": "string"},
                "profile_id": {"type": "string"},
                "default": {"type": "boolean", "default": False},
                "draft_text": {"type": "string", "description": "Draft to review, or the AI draft that human feedback refers to."},
                "argument_plan": {"type": "string"},
                "source_package": {"type": "string"},
                "review_focus": {"type": "array", "items": {"type": "string"}},
                "style_exemplar_categories": {"type": "array", "items": {"type": "string"}},
                "corpus_ids": {"type": "array", "items": {"type": "string"}},
                "tag": {"type": "string"},
                "content": {"type": "string", "description": "Direct style corpus content from a resolved user-owned boundary."},
                "source_title": {"type": "string"},
                "profile_json": {"type": "object"},
                "profile_markdown": {"type": "string"},
                "source_corpus_ids": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
                "original_text": {"type": "string"},
                "revised_text": {"type": "string"},
                "human_feedback": {"type": "string", "description": "Human review comments. Required for learning unless revised_text is present."},
                "base_profile_id": {"type": "string"},
                "provider_id": {"type": "string"},
                "set_default": {"type": "boolean", "default": True},
            },
            "required": ["action"],
        },
    },
    {
        "name": "syntara_external_search",
        "description": "Search external academic/source databases before importing into Syntara. Currently supports provider pubmed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "provider": {"type": "string", "enum": ["pubmed"], "default": "pubmed"},
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
            },
            "required": ["query"],
        },
    },
    {
        "name": "syntara_citations",
        "description": "Format citations in text or export BibTeX.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["format", "export_bibtex"]},
                "content": {"type": "string"},
                "style": {"type": "string", "enum": ["vancouver", "apa", "gb-t-7714"], "default": "vancouver"},
                "cite_keys": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["action"],
        },
    },
]


TOOLS = AGGREGATE_TOOLS


async def http_request(method: str, path: str, timeout: float | None = None, **kwargs: Any) -> Any:
    mark_backend_request_start()
    try:
        await ensure_backend()
        client = get_http_client()
        response = await client.request(method, path, timeout=timeout or TIMEOUT, **kwargs)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.text
    finally:
        mark_backend_request_end()


def get_http_client() -> httpx.AsyncClient:
    global HTTP_CLIENT
    if HTTP_CLIENT is None or HTTP_CLIENT.is_closed:
        HTTP_CLIENT = httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT)
    return HTTP_CLIENT


def mark_backend_request_start() -> None:
    global ACTIVE_REQUESTS
    ACTIVE_REQUESTS += 1


def mark_backend_request_end() -> None:
    global ACTIVE_REQUESTS, LAST_BACKEND_USED_AT
    ACTIVE_REQUESTS = max(0, ACTIVE_REQUESTS - 1)
    LAST_BACKEND_USED_AT = asyncio.get_running_loop().time()
    schedule_idle_shutdown()


def schedule_idle_shutdown() -> None:
    global IDLE_TASK
    if IDLE_SECONDS <= 0 or ACTIVE_REQUESTS > 0:
        return
    if not BACKEND_STARTED_BY_MCP or not BACKEND_PROCESS or BACKEND_PROCESS.returncode is not None:
        return
    if IDLE_TASK is not None and not IDLE_TASK.done():
        IDLE_TASK.cancel()
    IDLE_TASK = asyncio.create_task(stop_backend_after_idle())


async def stop_backend_after_idle() -> None:
    while True:
        if ACTIVE_REQUESTS > 0 or not BACKEND_STARTED_BY_MCP:
            return
        if not BACKEND_PROCESS or BACKEND_PROCESS.returncode is not None:
            return
        elapsed = asyncio.get_running_loop().time() - LAST_BACKEND_USED_AT
        remaining = IDLE_SECONDS - elapsed
        if remaining <= 0:
            await stop_backend_async()
            return
        await asyncio.sleep(remaining)


def clean_args(arguments: dict[str, Any] | None) -> dict[str, Any]:
    return {k: v for k, v in (arguments or {}).items() if v is not None}


async def call_tool(name: str, arguments: dict[str, Any] | None) -> Any:
    args = clean_args(arguments)

    if name == "syntara_status":
        action = args.get("action", "health")
        if action == "health":
            return await http_request("GET", "/api/health")
        if action == "list_projects":
            return await http_request("GET", "/api/projects")
        if action == "project_summary":
            return await http_request("GET", f"/api/projects/{project_slug(args['project'])}")
        raise ValueError(f"Unknown syntara_status action: {action}")

    if name == "syntara_retrieve":
        mode = args.get("mode", "search")
        if mode == "search":
            payload = {"query": args["query"], "scope": args.get("scope", "all"), "top_k": args.get("top_k", 10)}
            if args.get("project"):
                payload["project"] = project_slug(args["project"])
            return await http_request("POST", "/api/search", json=payload)
        if mode == "rag_answer":
            payload = {
                "question": args["question"],
                "search_scope": args.get("search_scope", args.get("scope", "all")),
                "top_k": args.get("top_k", 5),
                "use_tree": args.get("use_tree", True),
            }
            if args.get("provider_id"):
                payload["provider_id"] = args["provider_id"]
            if args.get("project"):
                payload["project"] = project_slug(args["project"])
            return await http_request("POST", "/api/ai/rag", json=payload, timeout=STYLE_TIMEOUT)
        if mode == "literature_grouped":
            payload = {"zh_query": args.get("zh_query", ""), "en_query": args.get("en_query", ""), "top_k": args.get("top_k", 10)}
            if args.get("provider_id"):
                payload["provider_id"] = args["provider_id"]
            if args.get("project"):
                payload["project"] = project_slug(args["project"])
            return await http_request("POST", "/api/search/literature-grouped", json=payload, timeout=STYLE_TIMEOUT)
        if mode == "chunk_context":
            payload = {"lit_id": args["lit_id"], "chunk_index": args["chunk_index"]}
            return await http_request("POST", "/api/search/chunk-context", json=payload)
        raise ValueError(f"Unknown syntara_retrieve mode: {mode}")

    if name == "syntara_sources":
        params = {"skip": args.get("skip", 0), "limit": args.get("limit", 20)}
        if args.get("tag"):
            params["tag"] = args["tag"]
        elif args.get("project"):
            params["tag"] = project_tag(args["project"])
        source_type = args.get("source_type", "literature")
        if source_type == "corpus":
            return await http_request("GET", "/api/corpus", params=params)
        if source_type != "literature":
            raise ValueError(f"Unknown syntara_sources source_type: {source_type}")
        params["sort_by"] = args.get("sort_by", "updated_at")
        params["order"] = args.get("order", "desc")
        return await http_request("GET", "/api/literature", params=params)

    if name == "syntara_import":
        source_type = args["source_type"]
        if source_type == "corpus_text":
            return await import_corpus_text(args)
        if source_type == "pubmed":
            return await import_pubmed(args)
        if source_type == "literature_pdfs":
            return await import_literature_pdfs(args)
        raise ValueError(f"Unknown syntara_import source_type: {source_type}")

    if name == "syntara_style_profile":
        return await style_profile_action(args)

    if name == "syntara_external_search":
        provider = args.get("provider", "pubmed")
        if provider == "pubmed":
            params = {"query": args["query"], "max_results": args.get("max_results", 20)}
            return await http_request("GET", "/api/pubmed/search", params=params)
        raise ValueError(f"Unknown syntara_external_search provider: {provider}")

    if name == "syntara_citations":
        action = args["action"]
        if action == "format":
            payload = {"content": args["content"], "style": args.get("style", "vancouver")}
            return await http_request("POST", "/api/documents/format-citations", json=payload)
        if action == "export_bibtex":
            cite_keys = ",".join(args.get("cite_keys") or [])
            return await http_request("GET", "/api/export/bibtex", params={"cite_keys": cite_keys})
        raise ValueError(f"Unknown syntara_citations action: {action}")

    raise ValueError(f"Unknown tool: {name}")


async def import_corpus_text(args: dict[str, Any]) -> Any:
    title = args["title"].strip()
    content = args["content"]
    tags = args.get("tags") or []
    if args.get("project"):
        tags = ensure_tag(tags, project_tag(args["project"]))
    description_parts = []
    if args.get("description"):
        description_parts.append(args["description"].strip())
    if args.get("source_url"):
        description_parts.append(f"Source URL: {args['source_url']}")
    if args.get("source_id"):
        description_parts.append(f"Source ID: {args['source_id']}")
    description = "\n".join(part for part in description_parts if part)
    filename = safe_filename(title) + ".md"
    if args.get("dry_run"):
        return {"ok": True, "dry_run": True, "title": title, "filename": filename, "characters": len(content), "tags": tags}
    files = {"file": (filename, content.encode("utf-8"), "text/markdown")}
    data = {"title": title, "description": description, "tags": ",".join(tags)}
    return await http_request("POST", "/api/corpus/upload", data=data, files=files)


async def import_pubmed(args: dict[str, Any]) -> Any:
    pmids = [str(pmid).strip() for pmid in args["pmids"] if str(pmid).strip()]
    if args.get("dry_run"):
        return {"ok": True, "dry_run": True, "pmids": pmids, "count": len(pmids)}
    result = await http_request("POST", "/api/pubmed/import", json=pmids, timeout=STYLE_TIMEOUT)
    if args.get("project"):
        await tag_literature_results(result.get("imported", []), project_tag(args["project"]))
    return result


async def import_literature_pdfs(args: dict[str, Any]) -> Any:
    pdf_paths = collect_pdf_paths(args)
    if args.get("dry_run"):
        return {"ok": True, "dry_run": True, "files": [str(path) for path in pdf_paths], "count": len(pdf_paths)}

    imported = []
    failed = []
    for path in pdf_paths:
        try:
            files = {"file": (path.name, path.read_bytes(), "application/pdf")}
            result = await http_request("POST", "/api/literature/import/pdf", files=files, timeout=STYLE_TIMEOUT)
            if args.get("project"):
                await tag_literature_results([result], project_tag(args["project"]))
            imported.append({"file": str(path), "result": result})
        except httpx.HTTPStatusError as exc:
            failed.append({"file": str(path), "error": f"HTTP {exc.response.status_code}: {exc.response.text}"})
        except Exception as exc:
            failed.append({"file": str(path), "error": str(exc)})
    return {"imported": imported, "failed": failed}


async def style_profile_action(args: dict[str, Any]) -> Any:
    action = args["action"]
    project = project_slug(args.get("project", "default"))
    if action == "list":
        params = {}
        if args.get("project"):
            params["project"] = project
        if args.get("style_type"):
            params["style_type"] = args["style_type"]
        return await http_request("GET", "/api/style-profiles", params=params)
    if action == "get":
        profile_id = args.get("profile_id") or args.get("id")
        if profile_id:
            return await http_request("GET", f"/api/style-profiles/{profile_id}")
        if args.get("default", False) or not args.get("name"):
            return await http_request("GET", "/api/style-profiles/default", params={"project": project})
        profiles = await http_request("GET", "/api/style-profiles", params={"project": project})
        for item in profiles.get("items", []):
            if item.get("name") == args["name"]:
                return await http_request("GET", f"/api/style-profiles/{item['id']}")
        raise ValueError("Style profile not found")
    if action == "build":
        payload = {
            "name": args["name"],
            "project": project,
            "style_type": args.get("style_type"),
            "corpus_ids": args.get("corpus_ids") or [],
            "set_default": args.get("set_default", True),
        }
        for key in ("tag", "content", "source_title", "provider_id"):
            if args.get(key):
                payload[key] = args[key]
        return await http_request("POST", "/api/style-profiles/build", json=payload, timeout=STYLE_TIMEOUT)
    if action == "save":
        payload = {
            "name": args["name"],
            "project": project,
            "style_type": args.get("style_type"),
            "profile_json": args.get("profile_json") or {},
            "profile_markdown": args["profile_markdown"],
            "source_corpus_ids": args.get("source_corpus_ids") or [],
            "tags": args.get("tags") or [],
            "set_default": args.get("set_default", True),
        }
        return await http_request("POST", "/api/style-profiles", json=payload)
    if action in {"update", "update_from_revision"}:
        payload = {
            "original_text": args["original_text"],
            "project": project,
            "set_default": args.get("set_default", True),
        }
        if args.get("revised_text"):
            payload["revised_text"] = args["revised_text"]
        if args.get("human_feedback"):
            payload["human_feedback"] = args["human_feedback"]
        if args.get("base_profile_id") is None and args.get("id"):
            payload["base_profile_id"] = args["id"]
        for key in ("base_profile_id", "name", "style_type", "source_title", "provider_id"):
            if args.get(key):
                payload[key] = args[key]
        return await http_request("POST", "/api/style-profiles/revision", json=payload, timeout=STYLE_TIMEOUT)
    if action == "prepare_review":
        draft_text = args.get("draft_text") or args.get("original_text") or ""
        if not draft_text.strip():
            raise ValueError("draft_text is required for prepare_review")
        profile = await resolve_style_profile(args)
        exemplars = select_style_exemplars(
            profile.get("profile_json", {}).get("style_exemplars") or [],
            args.get("style_exemplar_categories") or [],
        )
        return {
            "ok": True,
            "action": action,
            "style_profile": profile_summary(profile),
            "style_package": {
                "profile_markdown": clip_text(profile.get("profile_markdown", ""), 12000),
                "selected_style_exemplars": exemplars,
                "anti_ai": profile.get("profile_json", {}).get("anti_ai", {}),
                "revision_preferences": profile.get("profile_json", {}).get("revision_preferences", []),
            },
            "review_contract": {
                "must_use_style_package": True,
                "review_before_revise": True,
                "review_memo_only": True,
                "learning_requires_human_feedback_or_final_text": True,
            },
            "review_prompt": build_review_prompt(
                draft_text=draft_text,
                argument_plan=args.get("argument_plan", ""),
                source_package=args.get("source_package", ""),
                review_focus=args.get("review_focus") or [],
                profile=profile,
                exemplars=exemplars,
            ),
            "next_step": "Write a review memo first, then a revision plan, then the revised draft. Do not learn until the user provides feedback or a final version.",
        }
    if action == "learn_from_human_review":
        original_text = args.get("original_text") or args.get("draft_text") or ""
        revised_text = args.get("revised_text") or ""
        human_feedback = args.get("human_feedback") or ""
        if not original_text.strip():
            raise ValueError("original_text or draft_text is required for learning")
        if not revised_text.strip() and not human_feedback.strip():
            raise ValueError("human_feedback or revised_text is required for learning")
        profile = await resolve_style_profile(args)
        payload = {
            "original_text": original_text,
            "project": profile.get("project") or project,
            "base_profile_id": profile["id"],
            "source_title": args.get("source_title") or "human-reviewed writing",
            "set_default": args.get("set_default", True),
        }
        if revised_text.strip():
            payload["revised_text"] = revised_text
        if human_feedback.strip():
            payload["human_feedback"] = human_feedback
        if args.get("provider_id"):
            payload["provider_id"] = args["provider_id"]
        return await http_request("POST", "/api/style-profiles/revision", json=payload, timeout=STYLE_TIMEOUT)
    if action == "set_default":
        profile_id = args.get("profile_id") or args.get("id")
        if profile_id:
            return await http_request("PUT", f"/api/style-profiles/{profile_id}/default")
        profiles = await http_request("GET", "/api/style-profiles", params={"project": project})
        for item in profiles.get("items", []):
            if item.get("name") == args.get("name"):
                return await http_request("PUT", f"/api/style-profiles/{item['id']}/default")
        raise ValueError("Style profile not found")
    raise ValueError(f"Unknown style profile action: {action}")


async def resolve_style_profile(args: dict[str, Any]) -> dict[str, Any]:
    profile_id = args.get("profile_id") or args.get("id")
    if profile_id:
        return await http_request("GET", f"/api/style-profiles/{profile_id}")
    project = project_slug(args.get("project", "default"))
    if args.get("style_type"):
        profiles = await http_request("GET", "/api/style-profiles", params={"project": project, "style_type": args["style_type"]})
        items = profiles.get("items", [])
        if items:
            return await http_request("GET", f"/api/style-profiles/{items[0]['id']}")
    return await http_request("GET", "/api/style-profiles/default", params={"project": project})


def select_style_exemplars(exemplars: list[Any], categories: list[str], limit: int = 4) -> list[dict[str, Any]]:
    cleaned = [item for item in exemplars if isinstance(item, dict)]
    if categories:
        wanted = {str(category) for category in categories}
        matched = [item for item in cleaned if str(item.get("category", "")) in wanted]
        if matched:
            cleaned = matched
    return cleaned[:limit]


def profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": profile.get("id"),
        "name": profile.get("name"),
        "project": profile.get("project"),
        "style_type": profile.get("style_type") or profile.get("profile_json", {}).get("style_type"),
        "writing_mode": profile.get("profile_json", {}).get("writing_mode"),
        "exemplar_count": len(profile.get("profile_json", {}).get("style_exemplars") or []),
    }


def build_review_prompt(
    draft_text: str,
    argument_plan: str,
    source_package: str,
    review_focus: list[str],
    profile: dict[str, Any],
    exemplars: list[dict[str, Any]],
) -> str:
    focus_text = "\n".join(f"- {item}" for item in review_focus) or "- argument\n- evidence\n- structure\n- style\n- readability"
    exemplar_text = json.dumps(exemplars, ensure_ascii=False, indent=2)
    return f"""
Review this draft before revising it. Do not rewrite yet.

Use the style profile and style exemplars as mandatory review criteria, not optional inspiration.

Return a review memo with:
1. Argument issues.
2. Evidence or source-boundary issues.
3. Structure issues, especially places that copy the input outline instead of forming a real argument path.
4. Style alignment issues, including where the draft follows formatting but misses voice, judgment rhythm, paragraph breath, or explanation order.
5. AI-pattern issues.
6. A revision plan that says what to change and what to preserve.

Review focus:
{focus_text}

Style profile:
{clip_text(profile.get("profile_markdown", ""), 12000)}

Selected style exemplars:
{exemplar_text}

Argument plan:
{argument_plan or "(not provided)"}

Source package:
{source_package or "(not provided)"}

Draft:
{clip_text(draft_text, 30000)}
""".strip()


def clip_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[...trimmed...]"


def safe_filename(title: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", title, flags=re.UNICODE).strip("._")
    return cleaned[:80] or "workbuddy_corpus"


def project_tag(project: str) -> str:
    return f"project:{project_slug(project)}"


def project_slug(project: str) -> str:
    slug = project.strip()
    if slug.startswith("project:"):
        slug = slug.split(":", 1)[1]
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", slug).strip("-").lower()
    return slug or "default"


def ensure_tag(tags: list[str], tag: str) -> list[str]:
    cleaned = [str(item).strip() for item in tags if str(item).strip()]
    if tag not in cleaned:
        cleaned.append(tag)
    return cleaned


async def tag_literature_results(results: list[dict[str, Any]], tag: str) -> None:
    for item in results:
        lit_id = item.get("id")
        if not lit_id:
            continue
        tags = await http_request("GET", f"/api/literature/{lit_id}/tags")
        await http_request("PUT", f"/api/literature/{lit_id}", json={"tags": ensure_tag(tags, tag)})


def collect_pdf_paths(args: dict[str, Any]) -> list[Path]:
    paths = [Path(p).expanduser() for p in args.get("file_paths") or []]
    if args.get("folder_path"):
        folder = Path(args["folder_path"]).expanduser()
        pattern = "**/*.pdf" if args.get("recursive") else "*.pdf"
        paths.extend(sorted(folder.glob(pattern)))

    pdf_paths = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        if not path.is_file() or path.suffix.lower() != ".pdf":
            raise ValueError(f"Not a PDF file: {path}")
        pdf_paths.append(path)

    if not pdf_paths:
        raise ValueError("No PDF files provided")
    return pdf_paths


def read_message() -> dict[str, Any] | None:
    global MESSAGE_MODE
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line.lstrip().startswith(b"{"):
            MESSAGE_MODE = "jsonl"
            return json.loads(line.decode("utf-8"))
        if line in (b"\r\n", b"\n"):
            break
        key, _, value = line.decode("ascii").partition(":")
        headers[key.lower()] = value.strip()

    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))


def write_message(message: dict[str, Any]) -> None:
    body = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if MESSAGE_MODE == "jsonl":
        sys.stdout.buffer.write(body + b"\n")
        sys.stdout.buffer.flush()
        return
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def result_response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def tool_content(data: Any, is_error: bool = False) -> dict[str, Any]:
    text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2)
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def tool_error(error_type: str, message: str, retryable: bool = False, details: dict[str, Any] | None = None) -> dict[str, Any]:
    error = {"type": error_type, "message": message, "retryable": retryable}
    if details:
        error["details"] = details
    return {"error": error}


async def backend_healthy() -> bool:
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=3) as client:
            response = await client.get("/api/health")
        return response.status_code == 200
    except Exception:
        return False


async def ensure_backend() -> None:
    if await backend_healthy() or not AUTO_START:
        return

    parsed = urlparse(BASE_URL)
    host = parsed.hostname or "127.0.0.1"
    port = str(parsed.port or 8888)
    env = os.environ.copy()
    env["SYNTARA_HOST"] = host
    env["SYNTARA_PORT"] = port

    global BACKEND_ATEXIT_REGISTERED, BACKEND_LOG_FILE, BACKEND_PROCESS, BACKEND_STARTED_BY_MCP, LAST_BACKEND_USED_AT
    log_dir = BASE_DIR / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    BACKEND_LOG_FILE = (log_dir / "syntara_mcp_backend.log").open("ab")
    BACKEND_PROCESS = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "uvicorn", "backend.main:app", "--host", host, "--port", port,
        cwd=str(BASE_DIR),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=BACKEND_LOG_FILE,
        stderr=BACKEND_LOG_FILE,
    )
    BACKEND_STARTED_BY_MCP = True
    LAST_BACKEND_USED_AT = asyncio.get_running_loop().time()
    if not BACKEND_ATEXIT_REGISTERED:
        atexit.register(stop_backend)
        BACKEND_ATEXIT_REGISTERED = True

    for _ in range(40):
        if await backend_healthy():
            return
        if BACKEND_PROCESS.returncode is not None:
            return
        await asyncio.sleep(0.25)


def stop_backend() -> None:
    global BACKEND_LOG_FILE, BACKEND_STARTED_BY_MCP
    if BACKEND_STARTED_BY_MCP and BACKEND_PROCESS and BACKEND_PROCESS.returncode is None:
        BACKEND_PROCESS.terminate()
    BACKEND_STARTED_BY_MCP = False
    if BACKEND_LOG_FILE:
        BACKEND_LOG_FILE.close()
        BACKEND_LOG_FILE = None


async def stop_backend_async() -> None:
    global BACKEND_LOG_FILE, BACKEND_STARTED_BY_MCP
    if BACKEND_STARTED_BY_MCP and BACKEND_PROCESS and BACKEND_PROCESS.returncode is None:
        BACKEND_PROCESS.terminate()
        try:
            await asyncio.wait_for(BACKEND_PROCESS.wait(), timeout=5)
        except asyncio.TimeoutError:
            BACKEND_PROCESS.kill()
            await BACKEND_PROCESS.wait()
    BACKEND_STARTED_BY_MCP = False
    if BACKEND_LOG_FILE:
        BACKEND_LOG_FILE.close()
        BACKEND_LOG_FILE = None


async def handle_request(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    if request_id is None:
        return None

    if method == "initialize":
        return result_response(
            request_id,
            {
                "protocolVersion": SUPPORTED_PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "syntara", "version": "0.1.0"},
            },
        )

    if method == "tools/list":
        return result_response(request_id, {"tools": TOOLS})

    if method == "tools/call":
        try:
            name = params["name"]
            data = await call_tool(name, params.get("arguments") or {})
            return result_response(request_id, tool_content(data))
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            data = tool_error(
                "http_error",
                f"Syntara HTTP {status_code}",
                retryable=status_code >= 500,
                details={"status_code": status_code, "body": exc.response.text},
            )
            return result_response(request_id, tool_content(data, is_error=True))
        except httpx.TimeoutException as exc:
            data = tool_error("timeout", str(exc) or "Syntara request timed out", retryable=True)
            return result_response(request_id, tool_content(data, is_error=True))
        except httpx.RequestError as exc:
            data = tool_error("backend_unavailable", str(exc), retryable=True)
            return result_response(request_id, tool_content(data, is_error=True))
        except (KeyError, ValueError, FileNotFoundError) as exc:
            data = tool_error("invalid_request", str(exc), retryable=False)
            return result_response(request_id, tool_content(data, is_error=True))
        except Exception as exc:
            data = tool_error("unexpected_error", str(exc), retryable=False)
            return result_response(request_id, tool_content(data, is_error=True))

    if method == "ping":
        return result_response(request_id, {})

    return error_response(request_id, -32601, f"Method not found: {method}")


async def main() -> None:
    global HTTP_CLIENT
    try:
        while True:
            try:
                message = await asyncio.to_thread(read_message)
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                write_message(error_response(None, -32700, f"Parse error: {exc}"))
                continue
            if message is None:
                break
            response = await handle_request(message)
            if response is not None:
                write_message(response)
    finally:
        if HTTP_CLIENT is not None:
            await HTTP_CLIENT.aclose()
            HTTP_CLIENT = None


if __name__ == "__main__":
    asyncio.run(main())
