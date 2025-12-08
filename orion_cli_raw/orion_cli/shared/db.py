"""
ChromaDB Connection Manager
---------------------------
Canonical database access layer for Orion CNS.

- Loads Chroma once (singleton)
- Uses Jina-v2 embedding engine
- Ensures consistent vector dimension
- Provides persona / episodic / semantic collections
- Fully config-driven
"""

import threading

from chromadb import Client
from chromadb.config import Settings

from .paths import CHROMA_DIR
from .embedding import embed_text, VECTOR_DIM
from .config import config

# ------------------------------------------------------------------------------
# Embedding Function Wrapper (Chroma expects a callable class)
# ------------------------------------------------------------------------------


class OrionEmbeddingFunction:
    def __call__(self, input_texts):
        return embed_text(input_texts)


# ------------------------------------------------------------------------------
# Singleton Chroma Client
# ------------------------------------------------------------------------------

_chroma = None
_chroma_lock = threading.Lock()


def get_chroma():
    """
    Returns the single Chroma client instance.
    """
    global _chroma

    with _chroma_lock:
        if _chroma is not None:
            return _chroma

        CHROMA_DIR.mkdir(parents=True, exist_ok=True)

        _chroma = Client(
            Settings(chroma_db_impl="duckdb+parquet", persist_directory=str(CHROMA_DIR))
        )

        return _chroma


# ------------------------------------------------------------------------------
# Collection Loader
# ------------------------------------------------------------------------------


def get_collection(name: str):
    """
    Loads (or creates) a Chroma collection with the canonical
    embedding function and target dimension.
    """

    client = get_chroma()

    # Ensure embedder wrapper is attached
    embedder = OrionEmbeddingFunction()

    try:
        col = client.get_or_create_collection(
            name=name, embedding_function=embedder, metadata={"vector_dim": VECTOR_DIM}
        )

    except Exception as e:
        raise RuntimeError(f"[DB ERROR] Failed to create collection '{name}': {e}")

    # Validate dimension consistency
    meta = col.metadata or {}
    stored_dim = meta.get("vector_dim")

    if stored_dim and stored_dim != VECTOR_DIM:
        raise ValueError(
            f"[DIMENSION MISMATCH] Collection '{name}' uses dim={stored_dim}, "
            f"but embedding backend is dim={VECTOR_DIM}. "
            f"Fix config.yaml or rebuild the collection."
        )

    return col


# ------------------------------------------------------------------------------
# Predefined Named Collections
# ------------------------------------------------------------------------------


def persona_collection():
    return get_collection(
        config.get("ltm", {}).get("persona_collection", "orion_persona")
    )


def episodic_collection():
    return get_collection(
        config.get("ltm", {}).get("episodic_collection", "orion_episodic")
    )


def semantic_collection():
    """
    Not implemented yet — but here for CNS future-proofing.
    """
    return get_collection(
        config.get("ltm", {}).get("semantic_collection", "orion_semantic")
    )
