"""Pure-Python embedding using character n-gram feature hashing.

Produces fixed-dimension vectors without any external model dependency.
Quality is lower than neural embeddings but works completely offline.
"""

from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache

import numpy as np

from backend.config import EMBEDDING_DIM

# N-gram sizes to combine for richer representation
_NGRAM_SIZES = (2, 3, 4)


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer with lowering."""
    text = text.lower().strip()
    # Split on non-alphanumeric (keeps CJK characters as individual tokens)
    tokens = re.findall(r"[\w\u4e00-\u9fff\u3400-\u4dbf]+", text)
    return tokens


def _char_ngrams(text: str, n: int) -> list[str]:
    """Extract character n-grams from text."""
    text = text.lower().strip()
    if len(text) < n:
        return [text] if text else []
    return [text[i : i + n] for i in range(len(text) - n + 1)]


def _hash_feature(feature: str, dim: int) -> tuple[int, float]:
    """Hash a feature to a dimension index and sign (+1/-1)."""
    h = hashlib.md5(feature.encode("utf-8")).hexdigest()
    idx = int(h[:8], 16) % dim
    sign = 1.0 if int(h[8:10], 16) % 2 == 0 else -1.0
    return idx, sign


def embed_text(text: str) -> list[float]:
    """Generate a fixed-dimension embedding for a single text using feature hashing."""
    vec = np.zeros(EMBEDDING_DIM, dtype=np.float64)

    # Word unigrams
    tokens = _tokenize(text)
    for t in tokens:
        idx, sign = _hash_feature(f"w:{t}", EMBEDDING_DIM)
        vec[idx] += sign

    # Character n-grams
    for n in _NGRAM_SIZES:
        ngrams = _char_ngrams(text, n)
        for ng in ngrams:
            idx, sign = _hash_feature(f"c{n}:{ng}", EMBEDDING_DIM)
            vec[idx] += sign * 0.5  # weight n-grams lower than words

    # L2 normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    return vec.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts."""
    return [embed_text(t) for t in texts]
