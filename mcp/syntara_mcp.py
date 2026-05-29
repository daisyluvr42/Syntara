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
import time
from typing import Any
from pathlib import Path
from urllib.parse import urlparse

import httpx

BASE_URL = os.getenv("SYNTARA_BASE_URL", "http://127.0.0.1:8888").rstrip("/")
TIMEOUT = float(os.getenv("SYNTARA_MCP_TIMEOUT", "60"))
AUTO_START = os.getenv("SYNTARA_MCP_AUTO_START", "1") != "0"
BASE_DIR = Path(__file__).resolve().parents[1]
BACKEND_PROCESS: subprocess.Popen | None = None
MESSAGE_MODE = "headers"


TOOLS: list[dict[str, Any]] = [
    {
        "name": "syntara_health",
        "description": "Check Syntara backend health and library counts.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "syntara_list_projects",
        "description": "List Syntara project areas backed by project:<slug> tags.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "syntara_project_summary",
        "description": "Return counts for one Syntara project area.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project slug such as professional-book."},
            },
            "required": ["project"],
        },
    },
    {
        "name": "syntara_search",
        "description": "Search Syntara literature and/or user corpus with hybrid retrieval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
                "scope": {
                    "type": "string",
                    "enum": ["all", "literature", "corpus"],
                    "default": "all",
                },
                "top_k": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                "project": {"type": "string", "description": "Optional Syntara project slug."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "syntara_rag_answer",
        "description": "Answer one bounded question using Syntara RAG and return sources/cite keys.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "A narrow question to answer."},
                "search_scope": {
                    "type": "string",
                    "enum": ["all", "literature", "corpus"],
                    "default": "all",
                },
                "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
                "use_tree": {"type": "boolean", "default": True},
                "provider_id": {"type": "string", "description": "Optional Syntara AI provider id."},
                "project": {"type": "string", "description": "Optional Syntara project slug."},
            },
            "required": ["question"],
        },
    },
    {
        "name": "syntara_search_literature_grouped",
        "description": "Search literature and return document-level results with chunk indexes for context expansion.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "zh_query": {"type": "string", "description": "Chinese search query."},
                "en_query": {"type": "string", "description": "English search query."},
                "top_k": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                "provider_id": {"type": "string", "description": "Optional Syntara AI provider id for query translation."},
                "project": {"type": "string", "description": "Optional Syntara project slug."},
            },
        },
    },
    {
        "name": "syntara_get_chunk_context",
        "description": "Return surrounding context for a Syntara literature chunk.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lit_id": {"type": "string", "description": "Literature id from search results."},
                "chunk_index": {"type": "integer", "description": "Chunk index from search results."},
            },
            "required": ["lit_id", "chunk_index"],
        },
    },
    {
        "name": "syntara_list_literature",
        "description": "List Syntara literature records and citation metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skip": {"type": "integer", "default": 0, "minimum": 0},
                "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
                "tag": {"type": "string"},
                "sort_by": {
                    "type": "string",
                    "enum": ["title", "year", "created_at", "updated_at", "imported_at", "cite_key"],
                    "default": "updated_at",
                },
                "order": {"type": "string", "enum": ["asc", "desc"], "default": "desc"},
                "project": {"type": "string", "description": "Optional Syntara project slug."},
            },
        },
    },
    {
        "name": "syntara_list_corpus",
        "description": "List user-imported Syntara corpus entries such as prior book chapters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skip": {"type": "integer", "default": 0, "minimum": 0},
                "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
                "tag": {"type": "string"},
                "project": {"type": "string", "description": "Optional Syntara project slug."},
            },
        },
    },
    {
        "name": "syntara_import_corpus_text",
        "description": "Import text from WorkBuddy/Tencent Docs into Syntara corpus and build local FTS/vector indexes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Corpus title."},
                "content": {"type": "string", "description": "Markdown or plain text content to import."},
                "description": {"type": "string", "description": "Optional description."},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags such as style-corpus, tencent-docs, chapter-notes.",
                },
                "source_url": {"type": "string", "description": "Optional Tencent Docs URL."},
                "source_id": {"type": "string", "description": "Optional Tencent Docs file_id/node_id."},
                "project": {"type": "string", "description": "Optional Syntara project slug."},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "syntara_build_style_profile",
        "description": "Extract a reusable structured writing style profile from given corpus text or imported Syntara corpus entries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Style profile name, such as 公众号长文风格."},
                "project": {"type": "string", "description": "Project slug to attach the style profile to.", "default": "default"},
                "style_type": {"type": "string", "description": "Optional writing type, such as wechat-longform, professional-book, literature-review, tutorial, ppt."},
                "corpus_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional Syntara corpus ids to use as style examples.",
                },
                "tag": {"type": "string", "description": "Optional corpus tag to collect style examples from."},
                "content": {"type": "string", "description": "Optional direct style corpus content from WorkBuddy/ima/Tencent Docs."},
                "source_title": {"type": "string", "description": "Title for direct style corpus content."},
                "provider_id": {"type": "string", "description": "Optional Syntara AI provider id."},
                "set_default": {"type": "boolean", "default": True},
            },
            "required": ["name"],
        },
    },
    {
        "name": "syntara_list_style_profiles",
        "description": "List reusable Syntara writing style profiles, optionally scoped to one project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Optional project slug."},
                "style_type": {"type": "string", "description": "Optional writing type filter."},
            },
        },
    },
    {
        "name": "syntara_save_style_profile",
        "description": "Save an already extracted style profile into Syntara and optionally set it as project default.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Style profile name."},
                "project": {"type": "string", "description": "Project slug.", "default": "default"},
                "style_type": {"type": "string", "description": "Optional writing type, such as wechat-longform, professional-book, literature-review, tutorial, ppt."},
                "profile_json": {"type": "object", "description": "Optional structured profile JSON."},
                "profile_markdown": {"type": "string", "description": "Human-readable style profile markdown."},
                "source_corpus_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional Syntara corpus ids used to create the profile.",
                },
                "tags": {"type": "array", "items": {"type": "string"}},
                "set_default": {"type": "boolean", "default": True},
            },
            "required": ["name", "profile_markdown"],
        },
    },
    {
        "name": "syntara_get_style_profile",
        "description": "Get a Syntara style profile by id, by project/name, or the default profile for a project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile_id": {"type": "string"},
                "project": {"type": "string", "description": "Project slug.", "default": "default"},
                "name": {"type": "string", "description": "Style profile name."},
                "default": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "syntara_set_default_style_profile",
        "description": "Set one Syntara style profile as the default for its project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile_id": {"type": "string"},
                "project": {"type": "string"},
                "name": {"type": "string"},
            },
        },
    },
    {
        "name": "syntara_search_pubmed",
        "description": "Search PubMed from Syntara and return candidate PMIDs for literature import.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "PubMed search query."},
                "max_results": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
            },
            "required": ["query"],
        },
    },
    {
        "name": "syntara_import_pubmed",
        "description": "Import selected PubMed PMIDs into the Syntara literature library.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pmids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "PubMed IDs to import.",
                },
                "project": {"type": "string", "description": "Optional Syntara project slug."},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["pmids"],
        },
    },
    {
        "name": "syntara_import_literature_pdfs",
        "description": "Import local PDF files into the Syntara literature library and start extraction/indexing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Absolute or home-relative paths to PDF files.",
                },
                "folder_path": {
                    "type": "string",
                    "description": "Optional folder containing PDFs to import.",
                },
                "recursive": {"type": "boolean", "default": False},
                "project": {"type": "string", "description": "Optional Syntara project slug."},
                "dry_run": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "syntara_format_citations",
        "description": "Format [@citekey] markers in draft text through Syntara citation formatting.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Draft text containing [@citekey] markers."},
                "style": {
                    "type": "string",
                    "enum": ["vancouver", "apa", "gb-t-7714"],
                    "default": "vancouver",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "syntara_export_bibtex",
        "description": "Export BibTeX for selected cite keys, or all references if omitted.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cite_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional cite keys to export.",
                }
            },
        },
    },
]


async def http_request(method: str, path: str, **kwargs: Any) -> Any:
    ensure_backend()
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        response = await client.request(method, path, **kwargs)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.text


def clean_args(arguments: dict[str, Any] | None) -> dict[str, Any]:
    return {k: v for k, v in (arguments or {}).items() if v is not None}


async def call_tool(name: str, arguments: dict[str, Any] | None) -> Any:
    args = clean_args(arguments)

    if name == "syntara_health":
        return await http_request("GET", "/api/health")

    if name == "syntara_list_projects":
        return await http_request("GET", "/api/projects")

    if name == "syntara_project_summary":
        return await http_request("GET", f"/api/projects/{project_slug(args['project'])}")

    if name == "syntara_search":
        payload = {
            "query": args["query"],
            "scope": args.get("scope", "all"),
            "top_k": args.get("top_k", 10),
        }
        if args.get("project"):
            payload["project"] = project_slug(args["project"])
        return await http_request("POST", "/api/search", json=payload)

    if name == "syntara_rag_answer":
        payload = {
            "question": args["question"],
            "search_scope": args.get("search_scope", "all"),
            "top_k": args.get("top_k", 5),
            "use_tree": args.get("use_tree", True),
        }
        if args.get("provider_id"):
            payload["provider_id"] = args["provider_id"]
        if args.get("project"):
            payload["project"] = project_slug(args["project"])
        return await http_request("POST", "/api/ai/rag", json=payload)

    if name == "syntara_search_literature_grouped":
        payload = {
            "zh_query": args.get("zh_query", ""),
            "en_query": args.get("en_query", ""),
            "top_k": args.get("top_k", 10),
        }
        if args.get("provider_id"):
            payload["provider_id"] = args["provider_id"]
        if args.get("project"):
            payload["project"] = project_slug(args["project"])
        return await http_request("POST", "/api/search/literature-grouped", json=payload)

    if name == "syntara_get_chunk_context":
        payload = {"lit_id": args["lit_id"], "chunk_index": args["chunk_index"]}
        return await http_request("POST", "/api/search/chunk-context", json=payload)

    if name == "syntara_list_literature":
        params = {
            "skip": args.get("skip", 0),
            "limit": args.get("limit", 20),
            "sort_by": args.get("sort_by", "updated_at"),
            "order": args.get("order", "desc"),
        }
        if args.get("tag"):
            params["tag"] = args["tag"]
        if args.get("project"):
            params["tag"] = project_tag(args["project"])
        return await http_request("GET", "/api/literature", params=params)

    if name == "syntara_list_corpus":
        params = {"skip": args.get("skip", 0), "limit": args.get("limit", 20)}
        if args.get("tag"):
            params["tag"] = args["tag"]
        if args.get("project"):
            params["tag"] = project_tag(args["project"])
        return await http_request("GET", "/api/corpus", params=params)

    if name == "syntara_import_corpus_text":
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
            return {
                "ok": True,
                "dry_run": True,
                "title": title,
                "filename": filename,
                "characters": len(content),
                "tags": tags,
            }
        files = {"file": (filename, content.encode("utf-8"), "text/markdown")}
        data = {"title": title, "description": description, "tags": ",".join(tags)}
        return await http_request("POST", "/api/corpus/upload", data=data, files=files)

    if name == "syntara_build_style_profile":
        payload = {
            "name": args["name"],
            "project": project_slug(args.get("project", "default")),
            "style_type": args.get("style_type"),
            "corpus_ids": args.get("corpus_ids") or [],
            "set_default": args.get("set_default", True),
        }
        for key in ("tag", "content", "source_title", "provider_id"):
            if args.get(key):
                payload[key] = args[key]
        return await http_request("POST", "/api/style-profiles/build", json=payload)

    if name == "syntara_list_style_profiles":
        params = {}
        if args.get("project"):
            params["project"] = project_slug(args["project"])
        if args.get("style_type"):
            params["style_type"] = args["style_type"]
        return await http_request("GET", "/api/style-profiles", params=params)

    if name == "syntara_save_style_profile":
        payload = {
            "name": args["name"],
            "project": project_slug(args.get("project", "default")),
            "style_type": args.get("style_type"),
            "profile_json": args.get("profile_json") or {},
            "profile_markdown": args["profile_markdown"],
            "source_corpus_ids": args.get("source_corpus_ids") or [],
            "tags": args.get("tags") or [],
            "set_default": args.get("set_default", True),
        }
        return await http_request("POST", "/api/style-profiles", json=payload)

    if name == "syntara_get_style_profile":
        if args.get("profile_id"):
            return await http_request("GET", f"/api/style-profiles/{args['profile_id']}")
        project = project_slug(args.get("project", "default"))
        if args.get("default", False) or not args.get("name"):
            return await http_request("GET", "/api/style-profiles/default", params={"project": project})
        profiles = await http_request("GET", "/api/style-profiles", params={"project": project})
        for item in profiles.get("items", []):
            if item.get("name") == args["name"]:
                return await http_request("GET", f"/api/style-profiles/{item['id']}")
        raise ValueError("Style profile not found")

    if name == "syntara_set_default_style_profile":
        if args.get("profile_id"):
            return await http_request("PUT", f"/api/style-profiles/{args['profile_id']}/default")
        project = project_slug(args.get("project", "default"))
        profiles = await http_request("GET", "/api/style-profiles", params={"project": project})
        for item in profiles.get("items", []):
            if item.get("name") == args.get("name"):
                return await http_request("PUT", f"/api/style-profiles/{item['id']}/default")
        raise ValueError("Style profile not found")

    if name == "syntara_search_pubmed":
        params = {"query": args["query"], "max_results": args.get("max_results", 20)}
        return await http_request("GET", "/api/pubmed/search", params=params)

    if name == "syntara_import_pubmed":
        pmids = [str(pmid).strip() for pmid in args["pmids"] if str(pmid).strip()]
        if args.get("dry_run"):
            return {"ok": True, "dry_run": True, "pmids": pmids, "count": len(pmids)}
        result = await http_request("POST", "/api/pubmed/import", json=pmids)
        if args.get("project"):
            await tag_literature_results(result.get("imported", []), project_tag(args["project"]))
        return result

    if name == "syntara_import_literature_pdfs":
        pdf_paths = collect_pdf_paths(args)
        if args.get("dry_run"):
            return {
                "ok": True,
                "dry_run": True,
                "files": [str(path) for path in pdf_paths],
                "count": len(pdf_paths),
            }

        imported = []
        failed = []
        for path in pdf_paths:
            try:
                files = {"file": (path.name, path.read_bytes(), "application/pdf")}
                result = await http_request("POST", "/api/literature/import/pdf", files=files)
                if args.get("project"):
                    await tag_literature_results([result], project_tag(args["project"]))
                imported.append({"file": str(path), "result": result})
            except httpx.HTTPStatusError as exc:
                failed.append({"file": str(path), "error": f"HTTP {exc.response.status_code}: {exc.response.text}"})
            except Exception as exc:
                failed.append({"file": str(path), "error": str(exc)})
        return {"imported": imported, "failed": failed}

    if name == "syntara_format_citations":
        payload = {"content": args["content"], "style": args.get("style", "vancouver")}
        return await http_request("POST", "/api/documents/format-citations", json=payload)

    if name == "syntara_export_bibtex":
        cite_keys = ",".join(args.get("cite_keys") or [])
        return await http_request("GET", "/api/export/bibtex", params={"cite_keys": cite_keys})

    raise ValueError(f"Unknown tool: {name}")


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


def backend_healthy() -> bool:
    try:
        with httpx.Client(base_url=BASE_URL, timeout=3) as client:
            response = client.get("/api/health")
            return response.status_code == 200
    except Exception:
        return False


def ensure_backend() -> None:
    if backend_healthy() or not AUTO_START:
        return

    parsed = urlparse(BASE_URL)
    host = parsed.hostname or "127.0.0.1"
    port = str(parsed.port or 8888)
    env = os.environ.copy()
    env["SYNTARA_HOST"] = host
    env["SYNTARA_PORT"] = port

    global BACKEND_PROCESS
    BACKEND_PROCESS = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", host, "--port", port],
        cwd=str(BASE_DIR),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    atexit.register(stop_backend)

    for _ in range(40):
        if backend_healthy():
            return
        if BACKEND_PROCESS.poll() is not None:
            return
        time.sleep(0.25)


def stop_backend() -> None:
    if BACKEND_PROCESS and BACKEND_PROCESS.poll() is None:
        BACKEND_PROCESS.terminate()


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
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
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
            message_text = f"Syntara HTTP {exc.response.status_code}: {exc.response.text}"
            return result_response(request_id, tool_content(message_text, is_error=True))
        except Exception as exc:
            return result_response(request_id, tool_content(str(exc), is_error=True))

    if method == "ping":
        return result_response(request_id, {})

    return error_response(request_id, -32601, f"Method not found: {method}")


async def main() -> None:
    while True:
        message = await asyncio.to_thread(read_message)
        if message is None:
            break
        response = await handle_request(message)
        if response is not None:
            write_message(response)


if __name__ == "__main__":
    asyncio.run(main())
