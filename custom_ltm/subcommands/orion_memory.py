# custom_ltm/orion_memory.py
import os, time
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

class OrionMemory:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(self.path, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=self.path,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        self._embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        # Write to BOTH collections so chat retrieval can see it
        self._col_web = self._get_or_create_collection("orion_web_ltm")
        self._col_epi = self._get_or_create_collection("orion_episodic_ltm")

    def _get_or_create_collection(self, name: str):
        try:
            return self._client.get_collection(name, embedding_function=self._embed_fn)
        except Exception:
            return self._client.create_collection(name, embedding_function=self._embed_fn)

    def add(self, content: str, layer: str = "semantic", tags=None):
        tags = tags or []
        # unique-ish id to avoid collisions if we call add twice quickly
        base_id = f"web_{int(time.time() * 1000)}"
        for col, suffix in ((self._col_web, "web"), (self._col_epi, "epi")):
            col.add(
                documents=[content],
                metadatas=[{"layer": layer, "tags": ", ".join(tags)}],
                ids=[f"{base_id}_{suffix}"],
            )
