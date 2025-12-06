import json
import uuid
from orion_cli.utils.chroma_utils import get_client, _get_or_create, EMBED_FN

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def ingest_mock(path: str, replace=False):
    data = load_json(path)

    client = get_client()
    coll = _get_or_create("persona")

    if replace:
        try:
            coll.delete()
        except:
            pass
        coll = _get_or_create("persona")

    ids, docs, metas = [], [], []

    for entry in data:
        txt = entry["text"].strip()
        meta = entry.get("metadata", {})
        meta["source"] = "mock"

        ids.append(str(uuid.uuid4()))
        docs.append(txt)
        metas.append(meta)

    vectors = [EMBED_FN(t) for t in docs]
    coll.add(ids=ids, documents=docs, metadatas=metas, embeddings=vectors)

    print(f"[MOCK INGEST COMPLETE] Loaded {len(docs)} entries into persona.")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    p.add_argument("--replace", action="store_true")
    args = p.parse_args()
    ingest_mock(args.file, args.replace)
