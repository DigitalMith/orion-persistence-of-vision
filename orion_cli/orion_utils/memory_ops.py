# orion_utils/memory_ops.py

import re
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb import PersistentClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# Sentence splitting (basic)
def sentence_segment(text):
    sentences = re.split(r'(?<=[.!?]) +', text)
    return [s.strip() for s in sentences if len(s.strip()) > 0]

# Auto-tagging logic (placeholder — simple keyword-based tags)
def tag_sentences(sentence, extra_tags=None):
    tags = []
    if "Vermont" in sentence:
        tags.append("Vermont")
    if "Perkinsville" in sentence:
        tags.append("Perkinsville")
    if "market" in sentence:
        tags.append("market")
    if extra_tags:
        tags.extend(extra_tags)
    return list(set(tags))

# Embedding model setup
_embedding_model = SentenceTransformer("all-mpnet-base-v2")

def embed_sentence(text: str) -> list:
    return _embedding_model.encode(text, convert_to_numpy=True).tolist()

# Chroma client setup (persistent DB)
client = PersistentClient(path="C:/Orion/chroma_data")
collection = client.get_or_create_collection("orion_ltm", embedding_function=SentenceTransformerEmbeddingFunction(model_name="all-mpnet-base-v2"))

# Store sentence + metadata into ChromaDB
def store_to_chroma(sentence, tags, topic=None, subtopic=None, source=None, embedding=None):
    try:
        metadata = {
            "text": sentence,
            "tags": ", ".join(tags) if isinstance(tags, list) else tags,
            "topic": topic or "",
            "subtopic": subtopic or "",
            "source": source or "",
        }

        # Ensure no None values get passed
        metadata = {k: v for k, v in metadata.items() if v is not None}

        collection.add(
            documents=[sentence],
            metadatas=[metadata],
            ids=[f"mem_{hash(sentence)}"],
            embeddings=[embedding] if embedding else None,
        )
        return True
    except Exception as e:
        print(f"[✗] Failed to store: {e}")
        return False

# Deduplication: check if similar already exists
def search_similar(embedding, threshold=0.95):
    try:
        results = collection.query(
            query_embeddings=[embedding],
            n_results=1,
            include=["distances", "documents"]
        )
        if results["distances"][0] and results["distances"][0][0] < (1 - threshold):
            return {
                "text": results["documents"][0][0],
                "similarity": 1 - results["distances"][0][0]
            }
        return None
    except Exception as e:
        print(f"[!] Similarity search failed: {e}")
        return None
