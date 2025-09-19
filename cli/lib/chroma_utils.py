# cli/lib/chroma_utils.py
import os
from chromadb import PersistentClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# Pick embedding model from environment (fallback if not set)
# MODEL_NAME = os.environ.get("ORION_EMBED_MODEL", "all-MiniLM-L6-v2")
# EMBED_FN = SentenceTransformerEmbeddingFunction(model_name=MODEL_NAME)
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"  # ✅ THIS is the correct HF model name

EMBED_FN = SentenceTransformerEmbeddingFunction(model_name=MODEL_NAME)

def get_client(persist_dir="user_data/chroma_db"):
    """
    Return a PersistentClient for the given ChromaDB directory.
    Ensures the directory exists.
    """
    os.makedirs(persist_dir, exist_ok=True)
    return PersistentClient(path=persist_dir)

def get_collection(collection_name, embed_fn=EMBED_FN, persist_dir="user_data/chroma_db"):
    """
    Public wrapper to fetch or create a collection with consistent embedding function.
    """
    client = get_client(persist_dir)
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=embed_fn,
    )

def _get_or_create(name: str, *, cosine: bool = False, embed_fn=EMBED_FN, persist_dir="user_data/chroma_db"):
    """
    Internal helper for Orion LTM. Always binds the embedding function.
    Supports cosine distance when requested.
    """
    client = get_client(persist_dir)
    try:
        return client.get_or_create_collection(
            name=name,
            embedding_function=embed_fn,
            metadata={"hnsw:space": "cosine"} if cosine else None,
        )
    except Exception as e:
        print(f"[ERROR] Failed to get/create collection '{name}': {e}")
        raise
