import os
import logging
from pathlib import Path
from collections import defaultdict

def _print_summary(collection):
    all_entries = collection.get(include=["metadatas"], limit=1000)
    metas = all_entries.get("metadatas", [])
    grouped = defaultdict(list)
    for meta in metas:
        kind = (meta.get("kind") or "unknown").lower()
        topic = meta.get("topic", "<no-topic>")
        grouped[kind].append(topic)

    print(f"\n✅ Found {len(metas)} entries total:")
    for kind, topics in grouped.items():
        print(f"- {kind} ({len(topics)})")
        for topic in sorted(topics):
            print(f"  - {topic}")
            
def _read_text(path: Path):
    try:
        data = path.read_text(encoding="utf-8")
        return data, None
    except Exception as e:
        return None, str(e)

def run(args=None):
    from chromadb import PersistentClient

    chroma_path = os.getenv("ORION_CHROMA_PATH")
    if chroma_path:
        chroma_path = Path(chroma_path).resolve()
    else:
        chroma_path = Path(__file__).resolve().parents[2] / "user_data" / "chroma_db"

    client = PersistentClient(path=str(chroma_path))
    coll = client.get_collection("orion_persona_ltm")

    # Print grouped summary
    _print_summary(coll)

    # Print detailed entries
    entries = coll.get(include=["documents", "metadatas"], limit=1000)
    for i, (doc, meta) in enumerate(zip(entries["documents"], entries["metadatas"])):
        print(f"\n--- Entry {i+1} ---")
        print(f"  topic:    {meta.get('topic', 'N/A')}")
        print(f"  kind:     {meta.get('kind', 'N/A')}")
        print(f"  priority: {meta.get('priority', 'N/A')}")
        print(f"  active:   {meta.get('active', True)}")
        print(f"  content:  {doc[:160]}{'...' if len(doc) > 160 else ''}")
