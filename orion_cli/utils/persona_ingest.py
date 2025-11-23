import click
import yaml
import json

from orion_cli.orion_ltm_integration import initialize_chromadb_for_ltm, EMBED_FN
from orion_cli.utils.embedding import EMBED_FN
from orion_cli.core.ltm import add_documents_to_collection
from datetime import datetime


def load_yaml_documents(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(yaml.safe_load_all(f))


def normalize_metadata(doc):
    """Flatten lists and sanitize metadata keys for Chroma."""
    meta = {}
    if not isinstance(doc, dict):
        return meta

    for key, val in doc.items():
        if isinstance(val, list):
            meta[key] = ", ".join(str(v) for v in val)
        elif isinstance(val, (str, int, float, bool)):
            meta[key] = val
        else:
            # skip nested dicts or non-serializable types
            continue
    return meta


def ingest_yaml(path: str, kind: str = "persona", replace=True):
    """Ingest either YAML, JSON, or JSONL into ChromaDB depending on file extension."""
    documents = []

    # --- Choose parser based on file type ---
    lower_path = str(path).lower()

    if lower_path.endswith(".jsonl"):
        print(f"[orion_cli] Detected JSONL file: {path}")
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    documents.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"⚠️ Skipping malformed JSONL line: {e}")

    elif lower_path.endswith(".json"):
        print(f"[orion_cli] Detected JSON file: {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # ensure list of dicts
            documents = data if isinstance(data, list) else [data]
            print(f"[orion_cli] Loaded {len(documents)} JSON documents")
        except Exception as e:
            print(f"⚠️ Failed to parse JSON file {path}: {e}")
            return

    else:
        print(f"[orion_cli] Detected YAML file: {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                documents = list(yaml.safe_load_all(f))
            print(f"[orion_cli] Loaded {len(documents)} YAML documents")
        except Exception as e:
            print(f"⚠️ Failed to parse YAML file {path}: {e}")
            return

    # Convert loaded JSON docs into ingestable "blocks"
    blocks = []
    for doc in documents:
        if isinstance(doc, dict):
            user = doc.get("user")
            orion = doc.get("orion")
            text = (
                f"User: {user}\nOrion: {orion}"
                if user and orion
                else json.dumps(doc, ensure_ascii=False)
            )
            meta = {
                "source": kind,
                "timestamp": doc.get("timestamp", ""),
                "importance": 0.7,
            }
            blocks.append({"text": text, "metadata": meta})

    print(
        f"[orion_cli] Ingesting {len(blocks)} entries into ChromaDB under '{kind}' collection"
    )

    # ✅ Generate embeddings
    texts = [b["text"] for b in blocks]
    embeddings = EMBED_FN.embed_documents(texts)

    for i, b in enumerate(blocks):
        b["embedding"] = embeddings[i]

    # ✅ Debug output for first few entries
    print(f"[DEBUG] Blocks to ingest: {len(blocks)}")
    for i, b in enumerate(blocks[:3]):
        print(f"[DEBUG] Block {i}:")
        print(f"  Text: {b['text'][:60]}...")
        print(f"  Metadata: {b['metadata']}")
        print(f"  Embedding length: {len(b['embedding'])}")

    # ✅ Initialize ChromaDB collections
    persona_coll, episodic_coll = initialize_chromadb_for_ltm(EMBED_FN)
    collection = persona_coll if kind == "persona" else episodic_coll

    # ✅ Timestamp normalization
    for b in blocks:
        meta = b.get("metadata", {})
        ts = b.get("timestamp")
        src = b.get("source_file", "")
        if src and not meta.get("timestamp"):
            try:
                base = src.replace(".json", "").split("\\")[-1]
                dt = datetime.strptime(base, "%Y%m%d-%H-%M-%S")
                meta["timestamp"] = dt.isoformat()
            except Exception:
                meta["timestamp"] = datetime.now().isoformat()
        elif ts and not meta.get("timestamp"):
            try:
                meta["timestamp"] = datetime.strptime(ts, "%Y%m%d").isoformat()
            except Exception:
                meta["timestamp"] = datetime.now().isoformat()
        b["metadata"] = meta

    # ✅ Safe ingest
    add_documents_to_collection(collection, blocks, replace=replace)
    print(f"[orion_cli] ✅ {kind.capitalize()} ingest complete.")


@click.group()
def cli():
    pass


@cli.command("persona")
@click.option(
    "--path",
    required=True,
    type=click.Path(exists=True),
    help="Path to persona YAML file.",
)
@click.option("--replace", is_flag=True, help="Replace existing ChromaDB entries.")
def persona_ingest(path, replace):
    """Ingest persona YAML into ChromaDB."""
    ingest_yaml(path=path, kind="persona", replace=replace)


@cli.command("mock")
@click.option(
    "--path",
    required=True,
    type=click.Path(exists=True),
    help="Path to mock dialog YAML file.",
)
@click.option("--replace", is_flag=True, help="Replace existing ChromaDB entries.")
def mock_ingest(path, replace):
    """Ingest mock dialog YAML into ChromaDB."""
    ingest_yaml(path=path, kind="mock", replace=replace)


# ----------------------------------------------------------------------
# Orion ingest wrappers for programmatic calls (used by orion_ingest.py)
# ----------------------------------------------------------------------


def ingest_persona():
    """Wrapper to load default persona.yaml and ingest into ChromaDB."""
    default_path = "orion_cli/data/ingest/persona.yaml"
    print(f"[persona_ingest] Using default path: {default_path}")
    ingest_yaml(path=default_path, kind="persona", replace=True)


def ingest_mock_dialogs():
    """Wrapper to load default mock_orian_dialog.json and ingest into ChromaDB."""
    default_path = "orion_cli/data/ingest/mock_orian_dialog.json"
    print(f"[persona_ingest] Using default path: {default_path}")
    ingest_yaml(path=default_path, kind="mock", replace=True)


def ingest_ltm():
    """Wrapper for normalized long-term memory logs."""
    default_path = "orion_cli/data/ingest/normalized_logs.jsonl"
    print(f"[persona_ingest] Using default path: {default_path}")
    ingest_yaml(path=default_path, kind="ltm", replace=True)


if __name__ == "__main__":
    cli()
