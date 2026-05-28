"""AI Provider abstraction layer for LLM interactions."""

from __future__ import annotations

import json

import httpx

from backend.db.sqlite import get_connection
from backend.models.ai_config import AIProviderType, CLOUD_PROVIDER_REGISTRY


async def chat_completion(
    provider_id: str | None,
    messages: list[dict],
    max_tokens: int | None = None,
    temperature: float | None = None,
    stream: bool = False,
) -> str:
    """Send chat completion request to the configured LLM provider."""
    config = _get_provider_config(provider_id)
    if not config:
        raise ValueError("No AI provider configured. Please add one in Settings.")

    provider = config["provider"]
    api_base = config["api_base"]
    api_key = config["api_key"]
    model_id = config["model_id"]
    final_max_tokens = max_tokens or config["max_tokens"]
    final_temp = temperature if temperature is not None else config["temperature"]

    # For cloud providers, resolve from registry if api_base is empty
    registry_entry = CLOUD_PROVIDER_REGISTRY.get(provider)
    if registry_entry:
        if not api_base:
            api_base = registry_entry["api_base"]
        if not model_id:
            model_id = registry_entry["default_model"]
        protocol = registry_entry["protocol"]
    else:
        # Local providers — protocol is determined by provider type
        if provider in (AIProviderType.local_anthropic_compat.value, "local_anthropic_compat"):
            protocol = "anthropic"
        else:
            # local_openai_compat or legacy local_lmstudio
            protocol = "openai"

    if protocol == "anthropic":
        return await _anthropic_chat(api_base, api_key, model_id, messages, final_max_tokens, final_temp)
    else:
        return await _openai_chat(api_base, api_key, model_id, messages, final_max_tokens, final_temp)


async def _openai_chat(
    api_base: str,
    api_key: str | None,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> str:
    """OpenAI-compatible chat completion (works with LM Studio too)."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _anthropic_chat(
    api_base: str,
    api_key: str | None,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> str:
    """Anthropic Claude API chat completion."""
    headers = {
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    if api_key:
        headers["x-api-key"] = api_key

    # Convert messages: extract system message
    system_msg = ""
    user_messages = []
    for m in messages:
        if m["role"] == "system":
            system_msg = m["content"]
        else:
            user_messages.append(m)

    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": user_messages,
    }
    if system_msg:
        body["system"] = system_msg

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{api_base}/messages",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        # Anthropic returns content as a list of blocks
        content_blocks = data.get("content", [])
        return "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")


def _get_provider_config(provider_id: str | None) -> dict | None:
    """Get provider config from database."""
    conn = get_connection()
    if provider_id:
        row = conn.execute(
            "SELECT * FROM ai_provider_config WHERE id = ?", (provider_id,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM ai_provider_config WHERE is_default = 1"
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT * FROM ai_provider_config LIMIT 1"
            ).fetchone()

    if not row:
        return None

    return {
        "id": row["id"],
        "provider": row["provider"],
        "api_base": row["api_base"],
        "api_key": row["api_key"],
        "model_id": row["model_id"],
        "max_tokens": row["max_tokens"],
        "temperature": row["temperature"],
    }
