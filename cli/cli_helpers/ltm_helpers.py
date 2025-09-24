# cli/cli_helpers/ltm_helpers.py

import os
import uuid
import yaml
import chromadb
from sentence_transformers import SentenceTransformer
from cli.lib.chroma_utils import get_collection, EMBED_FN

# Cache the model so it only loads once
_MODEL = None

def get_embedding_model():
    """Return a shared embedding model, loaded only once."""
    global _MODEL
    if _MODEL is None:
        with open("cli/data/web_config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        hf_token = config.get("embedding", {}).get("hf_token")
        if hf_token:
            os.environ["HUGGINGFACE_HUB_TOKEN"] = hf_token

        model_name = config.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
        _MODEL = SentenceTransformer(model_name, local_files_only=False)  # force online mode
        print(f"[✅] Loaded embedding model: {model_name}")
    return _MODEL

def embed_fn(texts):
    """Embed a list of texts using the shared model."""
    model = get_embedding_model()
    return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True).tolist()

def embed_text(text: str):
    """Return normalized embedding for a single string."""
    return embed_fn([text])[0]

def embed_and_store(
    text: str,
    metadata: dict,
    role: str = "user",
    collection_name: str = None,
):
    """
    Embeds and stores a text chunk into Chroma using the embedding function.
    """
    from cli.lib.chroma_utils import get_collection, EMBED_FN

    if not text.strip():
        return

    # Move logic inside the function
    collection = get_collection(collection_name or "default", embed_fn=EMBED_FN)

    embedding = EMBED_FN([text])[0]

    collection.add(
        documents=[text],
        metadatas=[metadata],
        embeddings=[embedding],
        ids=[metadata.get("id") or str(uuid.uuid4())]
    )
    
