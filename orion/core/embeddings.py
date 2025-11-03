"""Embedding model using intfloat/e5-large-v2."""

from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    """Wrapper for the intfloat/e5-large-v2 embedding model."""
    
    DEFAULT_MODEL = "intfloat/e5-large-v2"
    
    def __init__(self, model_name: str = None):
        """
        Initialize the embedding model.
        
        Args:
            model_name: Name of the model to use. Defaults to intfloat/e5-large-v2
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the sentence transformer model."""
        print(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        print("Model loaded successfully")
    
    def encode(self, texts: Union[str, List[str]], 
               normalize: bool = True) -> np.ndarray:
        """
        Encode text(s) into embeddings.
        
        Args:
            texts: Single text string or list of texts
            normalize: Whether to normalize embeddings
            
        Returns:
            numpy array of embeddings
        """
        if isinstance(texts, str):
            texts = [texts]
        
        # E5 models expect "query: " or "passage: " prefix
        # For simplicity, we'll treat all as passages
        prefixed_texts = [f"passage: {text}" for text in texts]
        
        embeddings = self.model.encode(
            prefixed_texts,
            normalize_embeddings=normalize,
            show_progress_bar=False
        )
        
        return embeddings
    
    def encode_query(self, query: str, normalize: bool = True) -> np.ndarray:
        """
        Encode a query text with the appropriate prefix.
        
        Args:
            query: Query text
            normalize: Whether to normalize embeddings
            
        Returns:
            numpy array of the embedding
        """
        prefixed_query = f"query: {query}"
        embedding = self.model.encode(
            prefixed_query,
            normalize_embeddings=normalize,
            show_progress_bar=False
        )
        return embedding
    
    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self.model.get_sentence_embedding_dimension()
