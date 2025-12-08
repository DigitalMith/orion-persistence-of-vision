from sentence_transformers import SentenceTransformer
from orion_cli.utils.config import get_config
from pathlib import Path
import logging
import warnings
import contextlib
import io

warnings.filterwarnings("ignore", category=FutureWarning)

cfg = get_config()

BASE_DIR = Path(__file__).resolve().parents[2]

rel_path = cfg.get("embed_model_path", "").strip()
if rel_path:
    model_name = str((BASE_DIR / rel_path).resolve())
else:
    raise RuntimeError("embed_model_path missing from config.yaml")

expected_dim = cfg.get("embed_dim", 768)

# ---------------------------------------------------------
# Quiet model load (nuclear option)
# ---------------------------------------------------------
print("[orion_cli] 🧠 Loading embedding model...")

# Silence everything HuggingFace/Torch spits out
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("chromadb").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)

warnings.filterwarnings("ignore")

# Redirect stdout + stderr during model load
with (
    contextlib.redirect_stdout(io.StringIO()),
    contextlib.redirect_stderr(io.StringIO()),
):
    embedding_model = SentenceTransformer(model_name, trust_remote_code=True)

print("[orion_cli] 🧠 Embedding model loaded.")


# ---------------------------------------------------------
# Tone + Tag Estimator — Placeholder
# ---------------------------------------------------------
def estimate_tone_and_tags(text: str):
    lowered = text.lower()
    if any(word in lowered for word in ["love", "joy", "hope", "peace"]):
        tone = "positive"
    elif any(word in lowered for word in ["hate", "anger", "fear", "sad"]):
        tone = "negative"
    else:
        tone = "neutral"
    tags = [tone, "ltm"]
    return tone, tags


def embed_texts(texts: list[str], model=None):
    if model is None:
        model = EMBED_FN
    return model(texts)


# ---------------------------------------------------------
# OrionEmbeddingFunction
# ---------------------------------------------------------
class OrionEmbeddingFunction:
    def __init__(self, model):
        self.model = model  # SentenceTransformer instance

    def embed_documents(self, texts):
        return self.model.encode(
            texts, convert_to_numpy=True, normalize_embeddings=True
        ).tolist()

    def embed_query(self, text):
        return self.model.encode(
            [text], convert_to_numpy=True, normalize_embeddings=True
        ).tolist()[0]

    # NEW: updated to ChromaDB's required signature
    def __call__(self, input):
        # ChromaDB passes a LIST of strings as "input"
        return self.model.encode(
            input, convert_to_numpy=True, normalize_embeddings=True
        ).tolist()

    # Optional: compatibility alias for older Orion code
    def embed(self, texts):
        return self.model.encode(
            texts, convert_to_numpy=True, normalize_embeddings=True
        ).tolist()


# ---------------------------------------------------------
# ★ SINGLETON ★
# ---------------------------------------------------------
EMBED_FN = OrionEmbeddingFunction(embedding_model)


# ---------------------------------------------------------
# Manual test
# ---------------------------------------------------------
if __name__ == "__main__":
    sample = ["This is a test."]
    print(embed_texts(sample))
