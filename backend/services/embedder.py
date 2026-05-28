"""Embedding generation — dispatches to python / local / cloud backend."""

from __future__ import annotations

import httpx

from backend.config import (
    EMBEDDING_API_BASE,
    EMBEDDING_API_KEY,
    EMBEDDING_CLOUD_BRAND,
    EMBEDDING_CLOUD_REGISTRY,
    EMBEDDING_MODE,
    EMBEDDING_MODEL,
)


class EmbeddingServiceUnavailable(RuntimeError):
    """Raised when the embedding service cannot be reached or returns invalid data."""


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using the configured backend."""
    if not texts:
        return []

    mode = EMBEDDING_MODE.lower()

    if mode == "python":
        from backend.services.embedding_python import embed_texts
        return embed_texts(texts)

    if mode == "local":
        import backend.config as _cfg
        return await _api_embeddings(_cfg.EMBEDDING_API_BASE, None, texts, model=_cfg.EMBEDDING_MODEL)

    if mode == "cloud":
        # Resolve api_base and model from cloud brand registry
        import backend.config as _cfg
        brand = _cfg.EMBEDDING_CLOUD_BRAND
        registry = EMBEDDING_CLOUD_REGISTRY.get(brand, {})
        api_base = registry.get("api_base", EMBEDDING_API_BASE)
        model = _cfg.EMBEDDING_MODEL or registry.get("default_model", "")
        return await _api_embeddings(api_base, _cfg.EMBEDDING_API_KEY, texts, model=model)

    raise ValueError(f"Unknown EMBEDDING_MODE: {EMBEDDING_MODE}")


async def get_single_embedding(text: str) -> list[float] | None:
    """Generate embedding for a single text."""
    results = await get_embeddings([text])
    return results[0] if results else None


async def _api_embeddings(
    api_base: str,
    api_key: str | None,
    texts: list[str],
    model: str = "",
) -> list[list[float]]:
    """Call an OpenAI-compatible /embeddings endpoint."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{api_base}/embeddings",
                headers=headers,
                json={
                    "model": model or EMBEDDING_MODEL,
                    "input": texts,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if "data" not in data:
                raise EmbeddingServiceUnavailable(
                    "Embedding service returned an invalid response."
                )
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            return [d["embedding"] for d in sorted_data]
        except EmbeddingServiceUnavailable:
            raise
        except Exception as exc:
            raise EmbeddingServiceUnavailable(
                f"Embedding service unavailable at {api_base}"
            ) from exc
