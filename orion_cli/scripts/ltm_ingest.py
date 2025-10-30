import json
import argparse
from rich import print
from orion_cli.orion_ltm_integration import (
    initialize_chromadb_for_ltm,
    COLL_EPISODIC_SENT,
)
from orion_cli.core.ltm import get_or_create_embed_fn


def ingest_ltm_data(source, replace=False):
    print(f"[orion_cli] 📥 Loading LTM data from: [bold]{source}[/bold]")
    with open(source, "r", encoding="utf-8") as f:
        lines = [json.loads(line.strip()) for line in f if line.strip()]

    embed_fn = get_or_create_embed_fn()
    client, collections = initialize_chromadb_for_ltm(embed_fn=embed_fn)
    episodic_coll = collections["episodic"]

    if replace:
        print("[orion_cli] 🔄 Replacing episodic memory collection...")
        client.delete_collection(COLL_EPISODIC_SENT)
        client, collections = initialize_chromadb_for_ltm(embed_fn=embed_fn)
        episodic_coll = collections["episodic"]

    docs, ids, metas = [], [], []
    skipped = 0

    for i, entry in enumerate(lines):
        doc = None

        user = entry.get("user") or entry.get("USER")
        assistant = entry.get("assistant") or entry.get("ORION")

        if user and assistant:
            doc = f"USER: {user.strip()}\nASSISTANT: {assistant.strip()}"
        elif "document" in entry:
            doc = entry["document"].strip()

        if not doc:
            skipped += 1
            continue

        meta = entry.get("metadata", {})
        docs.append(doc)
        ids.append(f"ltm::{i}")
        metas.append(meta)

    if not docs:
        print("[red]⚠️ No valid dialog entries were parsed. Aborting.[/red]")
        return

    print(
        f"[green]➕ Ingesting {len(docs)} LTM documents (skipped {skipped})...[/green]"
    )
    try:
        episodic_coll.add(documents=docs, metadatas=metas, ids=ids)
        print(
            f"[✅] Ingestion complete. Total in episodic collection: {episodic_coll.count()}"
        )
    except Exception as e:
        print(f"[red]❌ Failed to ingest: {e}[/red]")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest enriched LTM memory into ChromaDB"
    )
    parser.add_argument("--source", required=True, help="Path to JSONL file")
    parser.add_argument(
        "--replace", action="store_true", help="Replace existing episodic memory"
    )
    args = parser.parse_args()

    ingest_ltm_data(source=args.source, replace=args.replace)


if __name__ == "__main__":
    main()
