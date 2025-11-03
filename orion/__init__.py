"""
Orion - A local LLM framework with persistent memory and emotion-weighted embeddings.
"""

__version__ = "0.1.0"

from orion.core.config import ConfigLoader
from orion.core.memory import MemoryManager
from orion.core.embeddings import EmbeddingModel
from orion.core.retrieval import RAGRetriever

__all__ = [
    "ConfigLoader",
    "MemoryManager",
    "EmbeddingModel",
    "RAGRetriever",
]
