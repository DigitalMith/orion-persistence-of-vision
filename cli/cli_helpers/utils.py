# cli_helpers/utils.py
from pathlib import Path
import yaml, re
import hashlib
import json
from typing import Dict, Any
from chromadb import PersistentClient

def init_collection(collection_name: str, persist_dir: str = "user_data/chroma_db"):
    client = PersistentClient(path=persist_dir)
    return client.get_or_create_collection(name=collection_name)
    
def normalize_topic(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def load_yaml_sections(yaml_path: str) -> Dict[str, Any]:
    """
    Load a YAML file and return its top-level sections as a dictionary.
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("YAML root must be a dictionary")

    return data

def embed_and_store(text: str, metadata: dict, role: str, collection):
    from sentence_transformers import SentenceTransformer

    # Load config
    with open("cli/data/web_config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    hf_token = config.get("embedding", {}).get("hf_token")

    if hf_token:
        os.environ["HUGGINGFACE_HUB_TOKEN"] = hf_token

    model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
    embedding = model.encode([text], convert_to_numpy=True)[0].tolist()
    

    doc_id = hashlib.sha1((text + json.dumps(metadata)).encode("utf-8")).hexdigest()

    collection.add(
        documents=[text],
        metadatas=[{
            **metadata,
            "source": role
        }],
        ids=[doc_id],
        embeddings=[embedding]
    )
