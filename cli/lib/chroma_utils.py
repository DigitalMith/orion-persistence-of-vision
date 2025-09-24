# cli/lib/chroma_utils.py
import os
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

EMBED_FN = SentenceTransformerEmbeddingFunction(
    model_name=MODEL_NAME,
    model_kwargs={"local_files_only": False}
)

# ✅ Optional test function for debugging vector size
def _debug_print_embedding_dim():
    try:
        test_vec = EMBED_FN(["test"])[0]
        print(f"[DEBUG] Embedding model '{MODEL_NAME}' dimension: {len(test_vec)}")
    except Exception as e:
        print("[ERROR] Failed to compute test embedding:", e)

def embed_fn(texts):
    return EMBED_MODEL.encode(texts, convert_to_numpy=True, normalize_embeddings=True).tolist()


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

# ✅ Only run this if script is directly executed
if __name__ == "__main__":
    _debug_print_embedding_dim()
