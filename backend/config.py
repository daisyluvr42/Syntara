"""Syntara configuration."""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STYLES_DIR = BASE_DIR / "styles"
TEMPLATES_DIR = BASE_DIR / "templates"

# Database
SQLITE_DB_PATH = DATA_DIR / "syntara.db"
CHROMADB_DIR = DATA_DIR / "chromadb"

# File storage
FILES_DIR = DATA_DIR / "files"
CORPUS_DIR = DATA_DIR / "corpus"

# Embedding configuration
# Mode: "python" (no model), "local" (local API), "cloud" (cloud API)
EMBEDDING_MODE = os.getenv("EMBEDDING_MODE", "local")
EMBEDDING_API_BASE = os.getenv("EMBEDDING_API_BASE", "http://localhost:1234/v1")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")
EMBEDDING_CLOUD_BRAND = os.getenv("EMBEDDING_CLOUD_BRAND", "openai")
EMBEDDING_DIM = 1024  # Used by all modes; python mode produces this dim via hashing

# Cloud embedding provider registry — brand → { api_base, default_model }
EMBEDDING_CLOUD_REGISTRY: dict[str, dict] = {
    "openai": {
        "display_name": "OpenAI",
        "api_base": "https://api.openai.com/v1",
        "default_model": "text-embedding-3-small",
    },
    "google": {
        "display_name": "Google (Gemini)",
        "api_base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "text-embedding-004",
    },
    "deepseek": {
        "display_name": "DeepSeek",
        "api_base": "https://api.deepseek.com/v1",
        "default_model": "deepseek-embedding",
    },
    "mistral": {
        "display_name": "Mistral AI",
        "api_base": "https://api.mistral.ai/v1",
        "default_model": "mistral-embed",
    },
    "cohere": {
        "display_name": "Cohere",
        "api_base": "https://api.cohere.com/v2",
        "default_model": "embed-multilingual-v3.0",
    },
    "zhipu": {
        "display_name": "Zhipu (GLM)",
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "embedding-3",
    },
    "qwen": {
        "display_name": "Alibaba Qwen",
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "text-embedding-v3",
    },
    "siliconflow": {
        "display_name": "SiliconFlow",
        "api_base": "https://api.siliconflow.cn/v1",
        "default_model": "BAAI/bge-m3",
    },
    "together": {
        "display_name": "Together AI",
        "api_base": "https://api.together.xyz/v1",
        "default_model": "togethercomputer/m2-bert-80M-8k-retrieval",
    },
    "fireworks": {
        "display_name": "Fireworks AI",
        "api_base": "https://api.fireworks.ai/inference/v1",
        "default_model": "nomic-ai/nomic-embed-text-v1.5",
    },
}

# PubMed API
PUBMED_API_KEY = os.getenv("PUBMED_API_KEY", "")
PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_RATE_LIMIT = 10 if PUBMED_API_KEY else 3  # req/s

# CrossRef API
CROSSREF_BASE_URL = "https://api.crossref.org/works"
CROSSREF_MAILTO = os.getenv("CROSSREF_MAILTO", "")  # polite pool

# Server
HOST = os.getenv("SYNTARA_HOST", "127.0.0.1")
PORT = int(os.getenv("SYNTARA_PORT", "8888"))

# Pandoc
PANDOC_PATH = os.getenv("PANDOC_PATH", "pandoc")

# Extraction cache (persisted OCR / structured parser results)
EXTRACT_CACHE_DIR = DATA_DIR / "extract_cache"

# Document tree cache (PageIndex-style hierarchical trees)
DOC_TREE_DIR = DATA_DIR / "doc_trees"

# OpenDataLoader PDF
ODL_OUTPUT_DIR = DATA_DIR / "odl_cache"
ODL_FORMAT = os.getenv("ODL_FORMAT", "json")
ODL_MODE = os.getenv("ODL_MODE", "fast")  # "fast" or "hybrid"

# Structured PDF extraction
PDF_STRUCTURED_ENGINE = os.getenv("PDF_STRUCTURED_ENGINE", "liteparse")
LITEPARSE_MAX_PAGES = int(os.getenv("LITEPARSE_MAX_PAGES", "1000"))
LITEPARSE_DPI = int(os.getenv("LITEPARSE_DPI", "150"))
LITEPARSE_OCR_SERVER_URL = os.getenv("LITEPARSE_OCR_SERVER_URL", "")
LITEPARSE_OCR_LANGUAGE = os.getenv("LITEPARSE_OCR_LANGUAGE", "zh")
LITEPARSE_NUM_WORKERS = int(os.getenv("LITEPARSE_NUM_WORKERS", "2"))

# Ensure data directories exist
for d in [DATA_DIR, CHROMADB_DIR, FILES_DIR, CORPUS_DIR, STYLES_DIR, TEMPLATES_DIR, ODL_OUTPUT_DIR, EXTRACT_CACHE_DIR, DOC_TREE_DIR]:
    d.mkdir(parents=True, exist_ok=True)
