import os
import json
import tqdm
from uuid import uuid4
from datetime import datetime
from pathlib import Path

from tqdm import tqdm
from chromadb import PersistentClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from orion_cli.orion_ltm_integration import initialize_chromadb_for_ltm
from orion_cli.utils.embedding import embed, get_embed_function
from orion_cli.utils.ltm_utils import get_relevant_ltm

CHROMA_PATH = "C:/Orion/text-generation-webui/user_data/chroma_db"
DEFAULT_EMBED_MODEL = "sentence-transformers/all-mpnet-base-v2"


def retrieve_ltm_context(query: str, collection, top_k: int = 6) -> list[str]:
    """
    Queries the episodic LTM collection with the user's pooled input.
    Returns a list of relevant memory documents.
    """
    try:
        results = collection.query(query_texts=[query], n_results=top_k)
        return results.get("documents", [[]])[0]
    except Exception as e:
        print(f"[orion_ltm] ⚠️ Failed to retrieve LTM context: {e}")
        return []


def get_or_create_embed_fn():
    return get_embed_function()


def get_embed_fn():
    model_name = os.environ.get("ORION_EMBED_MODEL", DEFAULT_EMBED_MODEL)
    try:
        return SentenceTransformerEmbeddingFunction(model_name=model_name)
    except Exception as e:
        raise RuntimeError(
            f"[orion_ltm] Failed to load embedding model '{model_name}': {e}"
        )


# ✅ Move this BEFORE any function that uses it
EMBED_FN = get_embed_fn()


def initialize_chromadb_for_ltm(
    embed_fn=None, persist_dir="C:/Orion/text-generation-webui/user_data/chroma_db"
):
    """
    Initializes ChromaDB collections for persona and episodic memory.
    Returns both the client and the collections for flexibility.
    Used by TGWUI extension and CLI ingestion.
    """
    os.makedirs(persist_dir, exist_ok=True)
    client = PersistentClient(path=persist_dir)

    if embed_fn is None:
        from orion_cli.utils.embedding import get_embed_function

        embed_fn = get_embed_function()

    try:
        persona_coll = client.get_or_create_collection(
            name="orion_persona_ltm",  # unified name for persona
            embedding_function=embed_fn,
            metadata={"hnsw:space": "cosine"},
        )
        episodic_coll = client.get_or_create_collection(
            name="orion_episodic_sent_ltm",
            embedding_function=embed_fn,
            metadata={"hnsw:space": "cosine"},
        )

        print("[orion_ltm] ✅ ChromaDB collections initialized.")
        # Return all so CLI can use `client.delete_collection()`
        return client, persona_coll, episodic_coll

    except Exception as e:
        print(f"[orion_ltm] ❌ Failed to initialize ChromaDB for LTM: {e}")
        raise


def clean_metadata(md):
    return {
        k: (str(v) if isinstance(v, list) else v)
        for k, v in md.items()
        if isinstance(v, (str, int, float, bool, list))
    }


def ingest_staged_jsonl(jsonl_path: Path, collection_name: str, persist_dir: Path):
    print(f"🚀 Ingesting from '{jsonl_path}'")
    print(f"🧠 Using ChromaDB path: {persist_dir}")
    print(f"📛 Collection name: {collection_name}")

    with open(jsonl_path, "r", encoding="utf-8") as f:
        lines = [json.loads(l.strip()) for l in f if l.strip()]

    print(f"🧾 Embedding {len(lines)} entries...")

    client = PersistentClient(path=str(persist_dir))
    coll = client.get_or_create_collection(name=collection_name)

    docs, ids, metas = [], [], []
    failed = 0

    for entry in tqdm(lines, desc="📥 Embedding", unit="entry"):
        try:
            doc = entry["text"]
            meta = entry.get("metadata", {})
            doc_id = entry.get("id", str(uuid4()))

            docs.append(doc)
            ids.append(doc_id)
            metas.append(clean_metadata(meta))
        except Exception as e:
            failed += 1
            print(f"⚠️ Failed to process entry: {e}")

    # ✅ Generate embeddings using shared model
    if docs:
        print("🧠 Generating embeddings...")
        embeddings = embed(docs)
        coll.add(documents=docs, metadatas=metas, ids=ids, embeddings=embeddings)
        print(f"✅ Ingested {len(docs)} entries into '{collection_name}'")

    if failed:
        print(f"⚠️ {failed} entries failed to ingest.")


# === Migrated from chroma_utils.py ===
def _get_or_create(
    name: str,
    *,
    cosine: bool = False,
    embed_fn=EMBED_FN,
    persist_dir="user_data/chroma_db",
):
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

def on_user_turn(text: str, episodic_coll):
    """
    Stores a user message into episodic memory.
    """
    try:
        doc_id = f"user_{uuid4().hex}"
        metadata = {
            "role": "user",
            "kind": "episodic",
            "timestamp": datetime.now().isoformat(),
            "importance": 0.7,
            "tone": "neutral",
            "topic": "user_input",
        }

        episodic_coll.add(documents=[text], metadatas=[metadata], ids=[doc_id])
    except Exception as e:
        print(f"[orion_ltm] ❌ Failed to log user turn: {e}")


def on_assistant_turn(text: str, episodic_coll):
    """
    Stores an assistant message into episodic memory.
    """
    try:
        doc_id = f"assistant_{uuid4().hex}"
        metadata = {
            "role": "assistant",
            "kind": "episodic",
            "timestamp": datetime.now().isoformat(),
            "importance": 0.6,
            "tone": "neutral",
            "topic": "assistant_reply",
        }
        episodic_coll.add(documents=[text], metadatas=[metadata], ids=[doc_id])
    except Exception as e:
        print(f"[orion_ltm] ❌ Failed to log assistant turn: {e}")
