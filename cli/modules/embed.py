# modules/embed.py

import chromadb
from modules.embedding_provider import get_embedder, get_model_name

# ⬇️ Adjust this path/model as needed
COLLECTION_NAME = "orion_episodic_sent_ltm"

# 🔌 Load embedding model
hf_embedder = get_embedder()

# 🔗 Chroma client & collection
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=hf_embedder)

def embed_text(text):
    return hf_embedder([text])[0]

def embed_and_store(text, metadata):
    embedding = embed_text(text)
    doc_id = metadata.get("timestamp") + "-" + metadata.get("file")  # or use file_utils.hash_content(text)

    collection.add(
        documents=[text],
        embeddings=[embedding],
        ids=[doc_id],
        metadatas=[metadata]
    )
    print(f"🧠 Embedded + stored: {doc_id}")

def assert_dim(embedding):
    if len(embedding) != 768:
        raise ValueError(f"Embedding has invalid dimension: {len(embedding)}")

