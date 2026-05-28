# Syntara

Syntara connects local RAG, project-scoped source libraries, and WorkBuddy skills to turn papers, notes, and private knowledge bases into cited chapters, reviews, slides, and reports.

## What It Includes

- A local FastAPI backend for literature, corpus, search, RAG, citations, and project-scoped libraries.
- A stdio MCP bridge for WorkBuddy integration.
- WorkBuddy skills for academic chapter writing and literature reviews.
- An optional web frontend for local library management.

## WorkBuddy MCP

Install or refresh the local WorkBuddy MCP entry:

```bash
python mcp/install_syntara_workbuddy.py
```

The MCP server exposes `syntara_*` tools for project listing, search, RAG answers, imports, citation formatting, and BibTeX export.

## Local Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./start.sh
```

Local libraries and vector indexes live under `data/` and are intentionally not committed.
