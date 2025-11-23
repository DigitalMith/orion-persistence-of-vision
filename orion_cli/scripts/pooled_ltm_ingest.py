import json

from orion_cli.utils.embedding import embed_texts
from orion_cli.core.ltm import add_documents_to_collection
from orion_cli.orion_ltm_integration import initialize_chromadb_for_ltm, EMBED_FN
from orion_cli.shared.tone import estimate_tone_and_emotion


def ingest_pooled(source, pool_size, replace):
    print(f"[📥] Pooled LTM ingest starting: {source}")

    # Load source JSONL
    with open(source, "r", encoding="utf-8") as f:
        entries = [json.loads(line.strip()) for line in f if line.strip()]

    blocks = []
    for i in range(0, len(entries), pool_size):
        chunk = entries[i : i + pool_size]
        if not chunk:
            continue

        user_concat = "\n".join([item["user"] for item in chunk if "user" in item])
        assistant_concat = "\n".join(
            [item["assistant"] for item in chunk if "assistant" in item]
        )

        tone, tags = estimate_tone_and_emotion(user_concat, assistant_concat)

        blocks.append(
            {
                "text": user_concat + "\n" + assistant_concat,
                "tone": tone,
                "tags": tags,
                "meta": {
                    "source": source,
                    "pooled": True,
                    "range": f"{i}-{i + pool_size}",  # Flatten list to string
                },
            }
        )

    texts = [b["text"] for b in blocks]
    embeddings = embed_texts(texts, model=EMBED_FN)

    for i, b in enumerate(blocks):
        b["embedding"] = embeddings[i]

    client, collections = initialize_chromadb_for_ltm(EMBED_FN)
    episodic_coll = collections.get("episodic")

    add_documents_to_collection(episodic_coll, blocks, replace=replace)
    print("[orion_cli] ✅ Ingest complete.")
