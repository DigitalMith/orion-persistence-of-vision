import json
import uuid
from orion_cli.utils.chroma_utils import get_client, _get_or_create, EMBED_FN

def load_jsonl(path):
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except:
                pass
    return out

def ingest_name_chat(path: str, replace=False):
    raw = load_jsonl(path)

    # Merge into a single origin block
    merged = "\n".join(entry.get("text", "") for entry in raw if entry.get("text"))

    client = get_client()
    coll = _get_or_create("persona")

    if replace:
        try:
            coll.delete()
        except:
            pass
        coll = _get_or_create("persona")

    meta = {
        "source": "autobiographical",
        "importance": 1.0,
        "persistent": True
    }

    emb = EMBED_FN(merged)

    coll.add(
        ids=[str(uuid.uuid4())],
        documents=[merged],
        metadatas=[meta],
        embeddings=[emb]
    )

    print("[NAME-CHAT INGEST COMPLETE] Stored autobiographical persona block.")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    p.add_argument("--replace", action="store_true")
    args = p.parse_args()
    ingest_name_chat(args.file, args.replace)
