# C:\Orion\text-generation-webui\custom_ltm\list_by_topic.py
import json, chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

TOPIC = "Perkinsville VT"

client = chromadb.PersistentClient(
    path=r"C:\Orion\text-generation-webui\user_data\chroma_db",
    settings=Settings(anonymized_telemetry=False, allow_reset=True),
)
embed = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
col = client.get_collection("orion_web_ltm", embedding_function=embed)

res = col.get(ids=None, limit=100)
docs, metas = res.get("documents", []), res.get("metadatas", [])
rows = []
for doc, meta in zip(docs, metas):
    tags = (meta or {}).get("tags", "")
    if TOPIC.lower() in (tags or "").lower():
        payload = json.loads(doc)
        rows.append((payload.get("source"), payload.get("date"), payload.get("hash")))
print(f"Found {len(rows)} docs for topic={TOPIC!r}")
for src, date, h in rows:
    print(f"- {src}  ({date})  #{h}")
