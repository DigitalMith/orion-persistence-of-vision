import json
import uuid
from pathlib import Path
from typing import List, Dict
from orion_cli.utils.chroma_utils import get_client, _get_or_create, EMBED_FN
from orion_cli.utils.config import get_config

# ---------- Hybrid Rules ----------
EMO_TAGS = ["sad", "happy", "angry", "frustrat", "lonely", "love", "hurt", "afraid",
            "melanch", "compassion", "tired", "meaning", "value", "grief"]

IDENTITY_TAGS = ["orion", "self", "identity", "who i am", "my name", "purpose"]

INSIGHT_TAGS = ["breakthrough", "realization", "i think", "pattern", "insight", "i realize"]

POOL_SIZE = 3


def is_strong_signal(text: str) -> bool:
    lower = text.lower()
    return any(t in lower for t in (EMO_TAGS + IDENTITY_TAGS + INSIGHT_TAGS))


def load_jsonl(path: str) -> List[Dict]:
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except:
                continue
    return data


def pool_chunks(items: List[str], size: int) -> List[str]:
    pooled = []
    for i in range(0, len(items), size):
        block = "\n".join(items[i:i+size])
        pooled.append(block)
    return pooled


def hybrid_process(entries: List[Dict]) -> List[Dict]:
    strong = []
    weak = []

    for e in entries:
        txt = e.get("text", "").strip()
        if not txt:
            continue

        if is_strong_signal(txt):
            strong.append({
                "id": str(uuid.uuid4()),
                "text": txt,
                "metadata": {"source": "episodic", "quality": "strong"}
            })
        else:
            weak.append(txt)

    pooled = pool_chunks(weak, POOL_SIZE)
    pooled_norm = [
        {
            "id": str(uuid.uuid4()),
            "text": block,
            "metadata": {"source": "episodic", "quality": "pooled"}
        }
        for block in pooled if block.strip()
    ]

    return strong + pooled_norm


def ingest_hybrid(path: str, replace: bool = False):
    cfg = get_config()
    coll_name = cfg.ltm.episodic_collection

    raw = load_jsonl(path)
    processed = hybrid_process(raw)

    client = get_client()
    coll = _get_or_create(coll_name)

    if replace:
        try:
            coll.delete()
        except:
            pass
        coll = _get_or_create(coll_name)

    ids = [e["id"] for e in processed]
    docs = [e["text"] for e in processed]
    metas = [e["metadata"] for e in processed]

    vectors = [EMBED_FN(t) for t in docs]

    coll.add(ids=ids, documents=docs, metadatas=metas, embeddings=vectors)

    print(f"\n[HYBRID INGEST COMPLETE]")
    print(f"Raw entries: {len(raw)}")
    print(f"Final entries stored: {len(processed)}")
    print(f"Strong: {sum(1 for e in processed if e['metadata']['quality']=='strong')}")
    print(f"Pooled: {sum(1 for e in processed if e['metadata']['quality']=='pooled')}")
    print(f"Collection: {coll_name}\n")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    p.add_argument("--replace", action="store_true")
    args = p.parse_args()
    ingest_hybrid(args.file, replace=args.replace)
