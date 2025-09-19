from chromadb import PersistentClient
from chromadb.config import Settings
from textwrap import shorten

DB_PATH = "user_data/chroma_db"
COLL = "orion_persona"

def cmd_persona_recall(args):
    client = PersistentClient(path=args.db, settings=Settings(anonymized_telemetry=False))
    coll = client.get_or_create_collection(COLL)
    res = coll.get(include=["documents", "metadatas"])
    ids, docs, metas = res.get("ids", []), res.get("documents", []), res.get("metadatas", [])
    if not ids:
        print("[persona] No persona entries found.")
        return
    print("\nPERSONA ENTRIES\n---------------")
    for i, (_id, doc, meta) in enumerate(zip(ids, docs, metas), 1):
        name = (meta or {}).get("name") or (meta or {}).get("topic") or "persona"
        ts = (meta or {}).get("timestamp", "unknown")
        summary = shorten((doc or "").replace("\n", " "), width=96, placeholder="…")
        print(f"{i:>3}. [{ts}] {name:20} | {summary}")
    print()
