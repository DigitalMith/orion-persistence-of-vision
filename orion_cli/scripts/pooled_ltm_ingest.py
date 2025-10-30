import argparse
import json
from orion_cli.core.ltm import embed_texts, add_documents_to_collection
from orion_cli.orion_ltm_integration import initialize_chromadb_for_ltm, EMBED_FN
from orion_cli.utils import estimate_tone_and_emotion


def pool_dialogs(dialogs, pool_size=3):
    pooled = []
    buffer = []
    for entry in dialogs:
        buffer.append(entry["content"])
        if len(buffer) == pool_size:
            pooled.append("\n".join(buffer))
            buffer = []
    if buffer:
        pooled.append("\n".join(buffer))
    return pooled


def pooled_ltm_ingest(path, pool_size=3):
    with open(path, "r", encoding="utf-8") as f:
        dialogs = [json.loads(line) for line in f if line.strip()]

    turns = [d for d in dialogs if d.get("role") == "assistant"]
    pooled_blocks = pool_dialogs(turns, pool_size)

    # Estimate tone and emotion per block (stub)
    documents = []
    for block in pooled_blocks:
        metadata = estimate_tone_and_emotion(block)
        documents.append({"text": block, "metadata": metadata})

    embeddings = embed_texts([doc["text"] for doc in documents], model=EMBED_FN)
    for i, doc in enumerate(documents):
        doc["embedding"] = embeddings[i]

    _, collections = initialize_chromadb_for_ltm(EMBED_FN)
    episodic_coll = collections.get("episodic")
    add_documents_to_collection(episodic_coll, documents)
    print(f"[ltm] Pooled memory blocks stored: {len(documents)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest pooled dialog blocks into Orion LTM"
    )
    parser.add_argument(
        "--ltm", type=str, required=True, help="Path to dialog JSONL file"
    )
    parser.add_argument("--pool", type=int, default=3, help="Number of turns per block")
    args = parser.parse_args()

    pooled_ltm_ingest(args.ltm, pool_size=args.pool)
