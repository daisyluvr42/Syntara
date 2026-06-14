"""AI assistant API router."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException

from backend.db.sqlite import get_connection
from backend.models.ai_config import (
    AIProviderConfigCreate,
    AIProviderConfigUpdate,
    AIRequest,
    CLOUD_PROVIDER_REGISTRY,
    EmbeddingConfig,
    RAGRequest,
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStepResult,
)
from backend.services.rag import ai_action, rag_query

router = APIRouter(prefix="/api/ai", tags=["ai"])


# --- AI Actions ---

@router.post("/action")
async def perform_ai_action(req: AIRequest):
    """Perform an AI action (summarize, translate, rewrite, expand, explain)."""
    try:
        result = await ai_action(
            action=req.action,
            text=req.text,
            provider_id=req.provider_id,
            source_lang=req.source_lang,
            target_lang=req.target_lang,
        )
        return {"result": result}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"AI service error: {str(e)}")


@router.post("/rag")
async def rag_question(req: RAGRequest):
    """RAG-based Q&A: search literature and generate answer."""
    try:
        result = await rag_query(
            question=req.question,
            provider_id=req.provider_id,
            search_scope=req.search_scope,
            top_k=req.top_k,
            use_tree=req.use_tree,
            project=req.project,
        )
        return result
    except Exception as e:
        raise HTTPException(502, f"AI service error: {str(e)}")


@router.post("/workflow", response_model=WorkflowResponse)
async def run_workflow(req: WorkflowRequest):
    """Run a chained AI workflow by feeding each step into the next."""
    if not req.steps:
        raise HTTPException(400, "Workflow steps are required")

    current_text = req.text
    step_results: list[WorkflowStepResult] = []

    try:
        for action in req.steps:
            current_text = await ai_action(
                action=action,
                text=current_text,
                provider_id=req.provider_id,
                source_lang=req.source_lang,
                target_lang=req.target_lang,
            )
            step_results.append(WorkflowStepResult(action=action, result=current_text))

        return WorkflowResponse(result=current_text, steps=step_results, completed=True)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        return WorkflowResponse(
            result=current_text,
            steps=step_results,
            completed=False,
            error=f"AI service error: {str(e)}",
        )


# --- Provider Config CRUD ---

@router.get("/provider-brands")
async def get_provider_brands():
    """Return available cloud provider brands with their metadata."""
    brands = []
    for key, info in CLOUD_PROVIDER_REGISTRY.items():
        brands.append({
            "key": key,
            "display_name": info["display_name"],
            "default_model": info["default_model"],
        })
    return brands


@router.get("/providers")
async def list_providers():
    """List all AI provider configurations."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM ai_provider_config").fetchall()
    items = []
    for r in rows:
        item = dict(r)
        # Mask API key
        if item.get("api_key"):
            item["api_key_set"] = True
            item["api_key"] = None
        else:
            item["api_key_set"] = False
        items.append(item)
    return items


@router.post("/providers")
async def create_provider(data: AIProviderConfigCreate):
    """Create a new AI provider configuration."""
    conn = get_connection()
    provider_id = str(uuid.uuid4())

    # Auto-fill cloud provider defaults
    api_base = data.api_base
    model_id = data.model_id
    if data.provider.value in CLOUD_PROVIDER_REGISTRY:
        registry = CLOUD_PROVIDER_REGISTRY[data.provider.value]
        if not api_base:
            api_base = registry["api_base"]
        if not model_id:
            model_id = registry["default_model"]
    else:
        # Local providers require api_base and model_id
        if not api_base:
            raise HTTPException(400, "api_base is required for local providers")
        if not model_id:
            raise HTTPException(400, "model_id is required for local providers")

    # If this is set as default, unset others
    if data.is_default:
        conn.execute("UPDATE ai_provider_config SET is_default = 0")

    conn.execute(
        """INSERT INTO ai_provider_config (id, provider, name, api_base, api_key, model_id, is_default, max_tokens, temperature)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            provider_id, data.provider.value, data.name, api_base,
            data.api_key, model_id, int(data.is_default),
            data.max_tokens, data.temperature,
        ),
    )
    conn.commit()
    return {"id": provider_id}


@router.put("/providers/{provider_id}")
async def update_provider(provider_id: str, data: AIProviderConfigUpdate):
    """Update an AI provider configuration."""
    conn = get_connection()
    row = conn.execute("SELECT id FROM ai_provider_config WHERE id = ?", (provider_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Provider not found")

    updates = data.model_dump(exclude_unset=True)

    if not updates:
        return {"ok": True}

    # If setting as default, unset others
    if updates.get("is_default") is True:
        conn.execute("UPDATE ai_provider_config SET is_default = 0")
    if "is_default" in updates:
        updates["is_default"] = int(bool(updates["is_default"]))

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [provider_id]
    conn.execute(f"UPDATE ai_provider_config SET {set_clause} WHERE id = ?", values)
    conn.commit()
    return {"ok": True}


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: str):
    """Delete an AI provider configuration."""
    conn = get_connection()
    row = conn.execute("SELECT id FROM ai_provider_config WHERE id = ?", (provider_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Provider not found")
    conn.execute("DELETE FROM ai_provider_config WHERE id = ?", (provider_id,))
    conn.commit()
    return {"ok": True}


# --- Embedding Config ---

@router.get("/embedding-config")
async def get_embedding_config():
    """Get current embedding configuration."""
    from backend.config import (
        EMBEDDING_MODE, EMBEDDING_API_BASE, EMBEDDING_API_KEY,
        EMBEDDING_MODEL, EMBEDDING_CLOUD_BRAND, EMBEDDING_CLOUD_REGISTRY,
    )
    return {
        "mode": EMBEDDING_MODE,
        "api_base": EMBEDDING_API_BASE,
        "api_key_set": bool(EMBEDDING_API_KEY),
        "model": EMBEDDING_MODEL,
        "cloud_brand": EMBEDDING_CLOUD_BRAND,
    }


@router.get("/embedding-brands")
async def get_embedding_brands():
    """Return available cloud embedding provider brands."""
    from backend.config import EMBEDDING_CLOUD_REGISTRY
    return [
        {"key": k, "display_name": v["display_name"], "default_model": v["default_model"]}
        for k, v in EMBEDDING_CLOUD_REGISTRY.items()
    ]


@router.put("/embedding-config")
async def update_embedding_config(data: EmbeddingConfig):
    """Update embedding configuration."""
    import backend.config as cfg
    cfg.EMBEDDING_MODE = data.mode
    cfg.EMBEDDING_API_BASE = data.api_base
    cfg.EMBEDDING_API_KEY = data.api_key
    cfg.EMBEDDING_MODEL = data.model
    cfg.EMBEDDING_CLOUD_BRAND = data.cloud_brand
    if data.cloud_brand:
        # Auto-set model to brand default if user didn't override
        registry = cfg.EMBEDDING_CLOUD_REGISTRY.get(data.cloud_brand, {})
        if not data.model and registry:
            cfg.EMBEDDING_MODEL = registry.get("default_model", "")

    conn = get_connection()
    now = datetime.now().isoformat()
    values = {
        "embedding.mode": cfg.EMBEDDING_MODE,
        "embedding.api_base": cfg.EMBEDDING_API_BASE,
        "embedding.api_key": cfg.EMBEDDING_API_KEY,
        "embedding.model": cfg.EMBEDDING_MODEL,
        "embedding.cloud_brand": cfg.EMBEDDING_CLOUD_BRAND,
    }
    conn.executemany(
        """
        INSERT INTO app_config (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        [(key, value, now) for key, value in values.items()],
    )
    conn.commit()
    return {"ok": True}
