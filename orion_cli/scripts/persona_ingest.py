import yaml
import click
from orion_cli.orion_ltm_integration import initialize_chromadb_for_ltm, EMBED_FN

# from orion_cli.core.ltm import embed_texts, add_documents_to_collection


def ingest_persona_yaml(path: str, replace=True):
    print(f"[orion_cli] Loading persona file: {path}")

    with open(path, "r", encoding="utf-8") as f:
        documents = list(yaml.safe_load_all(f))

    print(f"[orion_cli] Loaded {len(documents)} persona documents")

    blocks = []
    for doc in documents:
        text = doc.get("text") or doc.get("content")
        if not text:
            continue

        meta = {
            "emotion": doc.get("emotion", "neutral"),
            "tone": doc.get("tone", "measured"),
            "catalog": doc.get("catalog", "persona"),
            "weight": float(doc.get("weight", 1.0)),
        }

        blocks.append({"text": text, "metadata": meta})

    texts = [b["text"] for b in blocks]
    embeddings = embed_texts(texts, model=EMBED_FN)
    for i, b in enumerate(blocks):
        b["embedding"] = embeddings[i]

    print(f"[orion_cli] Ingesting {len(blocks)} persona entries into ChromaDB")

    client, collections = initialize_chromadb_for_ltm(EMBED_FN)
    persona_coll = collections.get("persona")
    add_documents_to_collection(persona_coll, blocks, replace=replace)
    print("[orion_cli] ✅ Persona ingest complete.")


@click.command("persona-ingest")
@click.option(
    "--path",
    required=True,
    type=click.Path(exists=True),
    help="Path to persona YAML file.",
)
@click.option("--replace", is_flag=True, help="Replace existing ChromaDB entries.")
def persona_ingest(path, replace):
    """CLI command to ingest persona YAML into ChromaDB."""
    ingest_persona_yaml(path=path, replace=replace)
