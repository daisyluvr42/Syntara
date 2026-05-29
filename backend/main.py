"""Syntara — Literature Management & Writing Workbench API Server."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import HOST, PORT
from backend.db.sqlite import get_connection, init_db
from backend.routers import ai, corpus, doc_tree, document, export, extract_cache, literature, project, pubmed, search, style_profile


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database
    init_db()
    # Recover items stuck in 'processing' from a previous crash
    from backend.routers.literature import recover_stuck_processing
    recover_stuck_processing()
    yield
    # Shutdown: close database connection
    conn = get_connection()
    conn.close()


app = FastAPI(
    title="Syntara",
    description="Literature Management & Writing Workbench",
    version="0.4.0",
    lifespan=lifespan,
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(literature.router)
app.include_router(search.router)
app.include_router(document.router)
app.include_router(pubmed.router)
app.include_router(ai.router)
app.include_router(corpus.router)
app.include_router(export.router)
app.include_router(extract_cache.router)
app.include_router(doc_tree.router)
app.include_router(project.router)
app.include_router(style_profile.router)


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    from backend.db.chromadb_store import get_collection_count
    from backend.services.pandoc import is_pandoc_available

    conn = get_connection()
    lit_count = conn.execute("SELECT COUNT(*) as c FROM literature").fetchone()["c"]
    doc_count = conn.execute("SELECT COUNT(*) as c FROM document").fetchone()["c"]
    corpus_count = conn.execute("SELECT COUNT(*) as c FROM corpus").fetchone()["c"]

    return {
        "status": "ok",
        "literature_count": lit_count,
        "document_count": doc_count,
        "corpus_count": corpus_count,
        "vector_count": get_collection_count(),
        "pandoc_available": is_pandoc_available(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
