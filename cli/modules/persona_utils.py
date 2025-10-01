# modules/persona_utils.py

import yaml
import json
import os
from datetime import datetime
from modules import embed, file_utils

def run_persona_check():
    path = "./data/persona.yaml"
    if not os.path.exists(path):
        print(f"⚠️ Persona file not found: {path}")
        return
    with open(path, "r", encoding="utf-8") as f:
        print(f.read())

def seed_persona(yaml_path):
    if not os.path.exists(yaml_path):
        print(f"❌ Persona YAML not found: {yaml_path}")
        return

    with open(yaml_path, "r", encoding="utf-8") as f:
        persona_data = yaml.safe_load(f)

    entries = []
    for trait, value in persona_data.items():
        if isinstance(value, str):
            entries.append({
                "text": f"{trait}: {value}",
                "topic": "persona",
                "trait": trait,
                "timestamp": datetime.utcnow().isoformat()
            })

    print(f"🧬 Seeding {len(entries)} persona entries into memory...")

    for item in entries:
        hash_id = file_utils.hash_content(item["text"])
        metadata = {
            "topic": item["topic"],
            "trait": item["trait"],
            "timestamp": item["timestamp"],
            "source": "persona-seed"
        }
        embed.embed_and_store(item["text"], metadata)

    print("✅ Persona seeding complete.")

def recall_persona():
    print("🔎 Fetching persona traits from ChromaDB...")

    import chromadb
    client = chromadb.Client()
    collection = client.get_or_create_collection("orion_episodic_sent_ltm")

    try:
        results = collection.get()
        docs = results.get("documents", [])
        metadatas = results.get("metadatas", [])

        persona_traits = {}
        for doc, meta in zip(docs, metadatas):
            if meta.get("topic") == "persona":
                trait = meta.get("trait", "unknown")
                persona_traits.setdefault(trait, []).append(doc)

        if not persona_traits:
            print("⚠️ No persona traits found in memory.")
            return

        print("🧠 Persona traits stored in memory:")
        for trait, entries in persona_traits.items():
            print(f"\n🔹 {trait.upper()}:")
            for e in entries:
                print(f"   • {e}")

    except Exception as e:
        print(f"❌ Recall failed: {e}")

