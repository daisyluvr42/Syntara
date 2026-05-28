"""AI provider configuration models."""

from __future__ import annotations

import uuid
from enum import Enum

from pydantic import BaseModel, Field


class AIProviderType(str, Enum):
    # Local providers — user supplies api_base + model_id + picks protocol
    local_openai_compat = "local_openai_compat"
    local_anthropic_compat = "local_anthropic_compat"
    # Cloud providers — preset api_base & protocol, user only supplies api_key
    openai = "openai"
    anthropic = "anthropic"
    google = "google"
    deepseek = "deepseek"
    mistral = "mistral"
    groq = "groq"
    together = "together"
    moonshot = "moonshot"
    zhipu = "zhipu"
    qwen = "qwen"
    siliconflow = "siliconflow"
    baichuan = "baichuan"
    cohere = "cohere"
    perplexity = "perplexity"
    fireworks = "fireworks"


CLOUD_PROVIDER_REGISTRY: dict[str, dict] = {
    "openai": {
        "display_name": "OpenAI",
        "api_base": "https://api.openai.com/v1",
        "protocol": "openai",
        "default_model": "gpt-4o",
    },
    "anthropic": {
        "display_name": "Anthropic (Claude)",
        "api_base": "https://api.anthropic.com/v1",
        "protocol": "anthropic",
        "default_model": "claude-sonnet-4-20250514",
    },
    "google": {
        "display_name": "Google (Gemini)",
        "api_base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "protocol": "openai",
        "default_model": "gemini-2.0-flash",
    },
    "deepseek": {
        "display_name": "DeepSeek",
        "api_base": "https://api.deepseek.com/v1",
        "protocol": "openai",
        "default_model": "deepseek-chat",
    },
    "mistral": {
        "display_name": "Mistral AI",
        "api_base": "https://api.mistral.ai/v1",
        "protocol": "openai",
        "default_model": "mistral-large-latest",
    },
    "groq": {
        "display_name": "Groq",
        "api_base": "https://api.groq.com/openai/v1",
        "protocol": "openai",
        "default_model": "llama-3.3-70b-versatile",
    },
    "together": {
        "display_name": "Together AI",
        "api_base": "https://api.together.xyz/v1",
        "protocol": "openai",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    },
    "moonshot": {
        "display_name": "Moonshot (Kimi)",
        "api_base": "https://api.moonshot.cn/v1",
        "protocol": "openai",
        "default_model": "moonshot-v1-8k",
    },
    "zhipu": {
        "display_name": "Zhipu (GLM)",
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "protocol": "openai",
        "default_model": "glm-4-flash",
    },
    "qwen": {
        "display_name": "Alibaba Qwen",
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "protocol": "openai",
        "default_model": "qwen-plus",
    },
    "siliconflow": {
        "display_name": "SiliconFlow",
        "api_base": "https://api.siliconflow.cn/v1",
        "protocol": "openai",
        "default_model": "Qwen/Qwen2.5-7B-Instruct",
    },
    "baichuan": {
        "display_name": "Baichuan",
        "api_base": "https://api.baichuan-ai.com/v1",
        "protocol": "openai",
        "default_model": "Baichuan4",
    },
    "cohere": {
        "display_name": "Cohere",
        "api_base": "https://api.cohere.com/v2",
        "protocol": "openai",
        "default_model": "command-r-plus",
    },
    "perplexity": {
        "display_name": "Perplexity",
        "api_base": "https://api.perplexity.ai",
        "protocol": "openai",
        "default_model": "sonar-pro",
    },
    "fireworks": {
        "display_name": "Fireworks AI",
        "api_base": "https://api.fireworks.ai/inference/v1",
        "protocol": "openai",
        "default_model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
    },
}


class AIProviderConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: AIProviderType = AIProviderType.local_openai_compat
    name: str = ""
    api_base: str = "http://localhost:1234/v1"
    api_key: str | None = None
    model_id: str = ""
    is_default: bool = False
    max_tokens: int = 4096
    temperature: float = 0.7


class AIProviderConfigCreate(BaseModel):
    provider: AIProviderType
    name: str
    api_base: str | None = None      # Required for local, auto-filled for cloud
    api_key: str | None = None
    model_id: str | None = None       # Required for local, defaults for cloud
    is_default: bool = False
    max_tokens: int = 4096
    temperature: float = 0.7


class AIProviderConfigUpdate(BaseModel):
    name: str | None = None
    api_base: str | None = None
    api_key: str | None = None
    model_id: str | None = None
    is_default: bool | None = None
    max_tokens: int | None = None
    temperature: float | None = None


class AIRequest(BaseModel):
    """Request for AI operations."""
    action: str  # summarize, translate, rewrite, expand, explain_term, etc.
    text: str
    provider_id: str | None = None
    source_lang: str = "en"
    target_lang: str = "zh"
    context_literature_ids: list[str] = Field(default_factory=list)


class RAGRequest(BaseModel):
    """Request for RAG-based Q&A."""
    question: str
    provider_id: str | None = None
    search_scope: str = "all"  # all, literature, corpus
    top_k: int = 5
    use_tree: bool = True  # Enable PageIndex-style tree navigation (Layer 2)
    project: str | None = None


class WorkflowRequest(BaseModel):
    """Request for running a chained AI workflow."""
    steps: list[str] = Field(default_factory=list)
    text: str
    provider_id: str | None = None
    source_lang: str = "en"
    target_lang: str = "zh"


class WorkflowStepResult(BaseModel):
    """One completed workflow step."""
    action: str
    result: str


class WorkflowResponse(BaseModel):
    """Response for a chained AI workflow."""
    result: str
    steps: list[WorkflowStepResult]
    completed: bool = True
    error: str | None = None


class EmbeddingConfig(BaseModel):
    """Embedding configuration."""
    mode: str = "python"  # python, local, cloud
    api_base: str = ""
    api_key: str = ""
    model: str = ""
    cloud_brand: str = ""
