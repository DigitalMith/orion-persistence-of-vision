import os
from pathlib import Path
from sentence_transformers import SentenceTransformer
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from dotenv import load_dotenv

# ✅ Always resolve absolute .env path inside orion_cli
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

print(f"🔍 Loaded ORION_EMBED_MODEL: {os.getenv('ORION_EMBED_MODEL')}")

DEFAULT_EMBED_MODEL = "intfloat/e5-large-v2"
EMBEDDING_DIM = 1024

# Force override if the env var is missing or incorrect
if not os.getenv("ORION_EMBED_MODEL") or "mpnet" in os.getenv("ORION_EMBED_MODEL"):
    os.environ["ORION_EMBED_MODEL"] = DEFAULT_EMBED_MODEL
    print(f"⚙️  Forcing ORION_EMBED_MODEL to default: {DEFAULT_EMBED_MODEL}")

# Load model from environment or default
MODEL_NAME = os.environ.get("ORION_EMBED_MODEL", DEFAULT_EMBED_MODEL)
print(f"[orion_cli] 🧠 Loading embedding model: {MODEL_NAME}")
embedding_model = SentenceTransformer(MODEL_NAME)

# Validate dimensionality
try:
    vec = embedding_model.encode(["test"], convert_to_numpy=True)[0]
    if len(vec) != EMBEDDING_DIM:
        raise ValueError(
            f"[orion_cli] ❌ Embedding model returned {len(vec)}D, expected {EMBEDDING_DIM}D."
        )
except Exception as e:
    print(f"[orion_cli] ❌ Embedding model failed validation: {e}")
    raise


# ✅ Core embedding function for ChromaDB integrations
def get_embed_function():
    try:
        return SentenceTransformerEmbeddingFunction(model_name=MODEL_NAME)
    except Exception as e:
        print(f"[orion_cli] ❌ Failed to initialize embedding function: {e}")
        raise


# ✅ Direct embedding utility (for persona/LTM ingestion)
def embed(texts: list[str]) -> list[list[float]]:
    return embedding_model.encode(
        texts, convert_to_numpy=True, normalize_embeddings=True
    ).tolist()


# ✅ Singleton for global import
EMBED_FN = get_embed_function()
