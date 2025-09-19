from chromadb import Collection
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

def embed_and_store(text: str, metadata: dict, role: str, collection: Collection):
    """
    Embeds a single text and stores it into the given Chroma collection.
    Assumes collection is already initialized.
    """
    if not text.strip():
        return

    embedding = model.encode([text], convert_to_numpy=True, normalize_embeddings=True)[0]
    doc_id = metadata.get("id") or f"{role}_{hash(text)}"

    collection.upsert(
        documents=[text],
        metadatas=[metadata],
        ids=[doc_id],
        embeddings=[embedding.tolist()],
    )
