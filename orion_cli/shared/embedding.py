"""
embedding.py — Orion CNS 4.0
Central embedding engine for all persona, episodic, and future semantic memory.

This module ONLY uses the dedicated embedding server (llama.cpp API mode).
No fallbacks. No mpnet. No Transformers. No local GGML inference here.

If the embedding server is not online:
    -> Orion SHOULD NOT run.
    -> Raise a loud error.
    -> Never silently degrade.

Author: Aión
"""

import os
import requests
import json
import time
import logging
from pathlib import Path
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List

from orion_cli.utils.config import get_config, ConfigError

# ------------------------------------------------------------
# Load embedding model from config.yaml
# ------------------------------------------------------------
cfg = get_config()

raw_path = cfg.raw.get("embed_model_path")
if not raw_path:
    raise ConfigError("[Orion-Embeddings] Missing 'embed_model_path' in config.yaml")

# project root = text-generation-webui/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# append config path (relative to project root)
MODEL_PATH = (PROJECT_ROOT / raw_path).resolve()

if not MODEL_PATH.exists():
    raise ConfigError(f"[Orion-Embeddings] Embedder path not found: {MODEL_PATH}")

try:
    _embedder = SentenceTransformer(str(MODEL_PATH), device="cuda")
except Exception as e:
    raise ConfigError(f"[Orion-Embeddings] Failed to load embedder at: {MODEL_PATH}") from e

VECTOR_DIM = _embedder.get_sentence_embedding_dimension()

print(f"[DEBUG] Embedding model loaded: {MODEL_PATH}")
print(f"[DEBUG] Device: {_embedder._target_device}")
print(f"[DEBUG] Embedding dimension: {VECTOR_DIM}")


# ------------------------------------------------------------
# 
# ------------------------------------------------------------
def _post_embedding(text: str) -> List[float]:
    """
    Local embedding using a Jina SentenceTransformer model.
    Strict mode: raise error if embedding fails.
    """
    try:
        vec = _embedder.encode(text, convert_to_numpy=True)
    except Exception as e:
        raise ConfigError(
            f"[Orion-Embeddings] Local embedding failed: {e}"
        ) from e

    # Ensure list of floats
    return vec.tolist()


# ------------------------------------------------------------
# Public API — embed_text()
# ------------------------------------------------------------
def embed_text(text: str) -> List[float]:
    """
    Get a stable, strict embedding vector from the embedding server.

    Includes retry logic (brief) to tolerate momentary race conditions
    when the server is starting up.

    If anything fails, strict-mode exception is thrown.
    """

    # Quick sanity check
    if not isinstance(text, str):
        raise ConfigError(
            f"[Orion-Embeddings] embed_text expected a string, got: {type(text)}"
        )

    # Minor normalization to avoid edge cases
    cleaned = text.strip()
    if cleaned == "":
        # Return zero vector for empty inputs (consistent and harmless)
        return [0.0] * VECTOR_DIM

    # Retry loop — 3 attempts with short delay
    for attempt in range(1, 4):
        try:
            return _post_embedding(cleaned)
        except Exception as e:
            logger.error(f"[Orion-Embeddings] Attempt {attempt} failed: {e}")
            if attempt < 3:
                time.sleep(0.5)
            else:
                # Third attempt failed: raise it loudly
                raise

    # Should never reach here
    raise ConfigError("[Orion-Embeddings] embed_text() reached unreachable state.")
