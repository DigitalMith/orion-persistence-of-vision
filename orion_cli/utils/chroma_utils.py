# orion_cli/utils/chroma_utils.py

from orion_cli.utils.embedding import get_embed_function
from chromadb import PersistentClient
import os

# Set up the shared embedding function
EMBED_FN = get_embed_function()


def get_client():
    """Create or return a ChromaDB PersistentClient with the configured path."""
    persist_dir = os.getenv("ORION_CHROMA_PATH", "user_data/chroma_db")
    return PersistentClient(path=persist_dir)


# Placeholder for collection setup, reuse across modules if needed
def _get_or_create(client, name, embed_fn=None):
    if embed_fn is None:
        embed_fn = EMBED_FN
    return client.get_or_create_collection(name=name, embedding_function=embed_fn)
