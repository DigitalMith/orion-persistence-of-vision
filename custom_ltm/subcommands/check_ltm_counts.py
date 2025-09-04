import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(
    path=r"C:\Orion\text-generation-webui\user_data\chroma_db",
    settings=Settings(anonymized_telemetry=False, allow_reset=True),
)
embed = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

try:
    col = client.get_collection("orion_web_ltm", embedding_function=embed)
except Exception:
    print("Collection 'orion_web_ltm' not found.")
    raise SystemExit(1)

print("Documents count:", col.count())

# Peek the last few inserts
ids = col.get(ids=None, limit=5)  # may not support order; still shows recent-ish
print("Sample metadatas:", ids.get("metadatas", [])[:2])
print("Sample doc excerpt:", (ids.get("documents", [""])[0] or "")[:250])
