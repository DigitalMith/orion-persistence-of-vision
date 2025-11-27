# orion_cli/utils/model_registry.py

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # -> text-generation-webui/

# All models managed by Orion CLI in one place
REGISTRY = {
    "embed": {
        "qwen": BASE_DIR / "orion_cli" / "models" / "embeddings" / "qwen",
        "intfloat": BASE_DIR / "orion_cli" / "models" / "embeddings" / "intfloat",
    },
    "llm": {
        "orion": BASE_DIR
        / "user_data"
        / "models"
        / "openhermes-2.5-mistral-7b.Q5_K_M.gguf",
    },
}


def resolve_embed(name: str):
    """
    Returns a path if 'name' matches a registered embedding model.
    Otherwise returns the raw name (HuggingFace remote id).
    """
    embed_map = REGISTRY["embed"]

    if name.lower() in embed_map:
        return embed_map[name.lower()].as_posix()
    return name  # fallback to HF id or absolute path
