import os
import json
import tqdm
from pathlib import Path
import yaml
from tqdm import tqdm
from orion_cli.orion_ltm_integration import initialize_chromadb_for_ltm, EMBED_FN

# Constants
ORION_DB_PATH = Path("orion_cli") / "db"
ORION_DATA_PATH = Path("orion_cli") / "data"
PERSONA_FILE = ORION_DATA_PATH / "persona.yaml"
MOCK_DIALOGS_FILE = ORION_DATA_PATH / "mock_orion_dialogs.jsonl"
EMBED_MODEL = os.environ.get(
    "ORION_EMBED_MODEL", "sentence-transformers/all-mpnet-base-v2"
)

# Initialize ChromaDB client and collection
client, collections = initialize_chromadb_for_ltm(EMBED_FN)
collection = collections.get("persona")  # or \"episodic\" depending on use


def load_yaml(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_jsonl(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def format_persona_for_ingest(persona_data):
    entries = []
    for section in persona_data.get("traits", []):
        entries.append(
            {
                "document": section,
                "metadata": {
                    "why_saved": "Persona trait",
                    "tags": "persona, trait, orion",
                    "tone": "descriptive",
                    "weight": 1.0,
                },
            }
        )
    if "biography" in persona_data:
        entries.append(
            {
                "document": persona_data["biography"],
                "metadata": {
                    "why_saved": "Persona biography",
                    "tags": "persona, biography, orion",
                    "tone": "narrative",
                    "weight": 1.0,
                },
            }
        )
    return entries


def ingest_documents(entries):
    for idx, entry in enumerate(tqdm(entries, desc="Ingesting persona and dialogs")):
        collection.add(
            documents=[entry["document"]],
            metadatas=[entry["metadata"]],
            ids=[f"orion-{idx:05d}"],
        )


def main():
    persona_data = load_yaml(PERSONA_FILE)
    persona_entries = format_persona_for_ingest(persona_data)
    mock_dialogs = load_jsonl(MOCK_DIALOGS_FILE)
    all_entries = persona_entries + mock_dialogs
    ingest_documents(all_entries)
    print("✅ Persona and mock dialogs successfully ingested.")


if __name__ == "__main__":
    main()
