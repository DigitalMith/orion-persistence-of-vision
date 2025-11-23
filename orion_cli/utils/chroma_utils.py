# orion_cli/utils/chroma_utils.py

# -------------------------------------------------------------
# Orion / Chroma Utils — FINAL CLEAN VERSION
# -------------------------------------------------------------
# Includes:
#   - Nuclear telemetry override (before importing chromadb)
#   - Clean imports
#   - get_client()
#   - _get_or_create()
# -------------------------------------------------------------

# --- Nuclear telemetry override (must run BEFORE importing chromadb) ---
import sys
import types

_fake = types.SimpleNamespace(
    capture=lambda *args, **kwargs: None,
    telemetry=lambda *args, **kwargs: None,
    opentelemetry=lambda *args, **kwargs: None,
)

# Replace telemetry modules BEFORE Chroma loads them
sys.modules["chromadb.telemetry"] = _fake
sys.modules["chromadb.telemetry.posthog"] = _fake
sys.modules["chromadb.utils.telemetry"] = _fake

# -------------------------------------------------------------
# Normal imports
# -------------------------------------------------------------
from pathlib import Path
import os
import json

from chromadb import PersistentClient
from chromadb.config import Settings

from orion_cli.utils.embedding import EMBED_FN


# -------------------------------------------------------------
# Chroma client creation
# -------------------------------------------------------------
def get_client():
    """
    Create or return a ChromaDB PersistentClient using the ORION_CHROMA_PATH.
    """
    persist_dir = os.getenv("ORION_CHROMA_PATH", "user_data/Chroma-DB")
    return PersistentClient(path=persist_dir)


# -------------------------------------------------------------
# Get or create a collection
# -------------------------------------------------------------
def _get_or_create(client, name, embed_fn=None):
    """
    Get or create a Chroma collection using the correct embedding function.
    """
    if embed_fn is None:
        embed_fn = EMBED_FN

    return client.get_or_create_collection(
        name=name,
        embedding_function=embed_fn
    )
