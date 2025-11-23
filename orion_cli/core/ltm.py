import json
from uuid import uuid4
from pathlib import Path

from tqdm import tqdm

from orion_cli.utils.chroma_utils import get_client, EMBED_FN
from orion_cli.utils.embedding import EMBED_FN

CHROMA_PATH = "C:/Orion/text-generation-webui/user_data/Chroma-DB"


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


def get_embed_fn():
    return EMBED_FN


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
        lines = [json.loads(line.strip()) for line in f if line.strip()]

    print(f"🧾 Embedding {len(lines)} entries...")

    client = get_client()
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
def _get_or_create(client, name: str, embed_fn=EMBED_FN, cosine: bool = False):
    """
    Retrieve or create a ChromaDB collection with a proper embedding function.
    Ensures the collection always has a valid embed_fn bound.
    """
    try:
        collection = client.get_or_create_collection(
            name=name,
            embedding_function=embed_fn or EMBED_FN,
            metadata={"hnsw:space": "cosine"} if cosine else None,
        )

        # ✅ Defensive sanity check
        if not getattr(collection, "embedding_function", None):
            print(f"[ltm] ⚠️ Collection '{name}' missing embed_fn, rebinding manually.")
            collection.embedding_function = embed_fn or EMBED_FN

        return collection

    except Exception as e:
        print(f"[ERROR] Failed to get/create collection '{name}': {e}")
        raise


def add_documents_to_collection(collection, documents, replace=False):
    """
    Add documents to the given ChromaDB collection.

    Args:
        collection: The ChromaDB collection instance.
        documents: A list of dicts with 'text' and 'embedding' at minimum.
        replace: If True, will replace existing entries with the same ID.
    """
    ids = [str(uuid4()) for _ in documents]
    texts = [doc["text"] for doc in documents]
    embeddings = [doc["embedding"] for doc in documents]
    metadatas = [doc.get("metadata", {}) for doc in documents]

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )
