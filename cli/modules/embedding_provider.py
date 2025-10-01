# modules/embedding_provider.py

from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

# Single source of truth for embedding setup
def get_embedder():
    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL_NAME)

def get_model_name():
    return MODEL_NAME

def get_vector_dim():
    return 768  # Hardcoded for now, you can fetch from model later if dynamic
