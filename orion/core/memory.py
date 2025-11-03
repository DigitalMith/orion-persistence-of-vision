"""Memory management using ChromaDB with emotion weighting."""

from typing import Dict, List, Optional, Any
from pathlib import Path
import time
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from orion.core.embeddings import EmbeddingModel


class MemoryManager:
    """Manage long-term memory storage using ChromaDB."""
    
    def __init__(self, 
                 db_path: str = "./chroma_data",
                 collection_name: str = "orion_memory",
                 embedding_model: Optional[EmbeddingModel] = None):
        """
        Initialize the memory manager.
        
        Args:
            db_path: Path to ChromaDB storage directory
            collection_name: Name of the collection to use
            embedding_model: EmbeddingModel instance. If None, creates new one.
        """
        self.db_path = Path(db_path)
        self.collection_name = collection_name
        self.embedding_model = embedding_model or EmbeddingModel()
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create or get collection
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        """Get existing collection or create a new one."""
        try:
            collection = self.client.get_collection(name=self.collection_name)
            print(f"Loaded existing collection: {self.collection_name}")
        except Exception:
            # Catch any exception (collection not found, connection issues, etc.)
            # and create a new collection
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"Created new collection: {self.collection_name}")
        
        return collection
    
    def add_memory(self, 
                   text: str, 
                   metadata: Optional[Dict[str, Any]] = None,
                   emotion: Optional[float] = None,
                   memory_id: Optional[str] = None) -> str:
        """
        Add a memory to the database.
        
        Args:
            text: The text content to store
            metadata: Additional metadata to store with the memory
            emotion: Emotion weight (0.0 to 1.0). Higher values indicate stronger emotional content
            memory_id: Optional custom ID. If None, generates timestamp-based ID
            
        Returns:
            The ID of the stored memory
        """
        if memory_id is None:
            memory_id = f"mem_{int(time.time() * 1000000)}"
        
        # Prepare metadata
        meta = metadata or {}
        meta['timestamp'] = time.time()
        
        if emotion is not None:
            meta['emotion'] = float(emotion)
        
        # Generate embedding
        embedding = self.embedding_model.encode(text)
        
        # Store in ChromaDB
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding.tolist()],
            documents=[text],
            metadatas=[meta]
        )
        
        return memory_id
    
    def add_memories(self, 
                     texts: List[str],
                     metadatas: Optional[List[Dict[str, Any]]] = None,
                     emotions: Optional[List[float]] = None) -> List[str]:
        """
        Add multiple memories in batch (pooled memory storage).
        
        Args:
            texts: List of text contents to store
            metadatas: List of metadata dicts
            emotions: List of emotion weights
            
        Returns:
            List of memory IDs
        """
        if not texts:
            return []
        
        # Generate IDs
        ids = [f"mem_{int(time.time() * 1000000)}_{i}" for i in range(len(texts))]
        
        # Prepare metadatas
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        # Add timestamps and emotions
        current_time = time.time()
        for i, meta in enumerate(metadatas):
            meta['timestamp'] = current_time
            if emotions and i < len(emotions):
                meta['emotion'] = float(emotions[i])
        
        # Generate embeddings
        embeddings = self.embedding_model.encode(texts)
        
        # Store in ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas
        )
        
        return ids
    
    def query(self, 
              query_text: str,
              n_results: int = 5,
              where: Optional[Dict] = None,
              emotion_boost: bool = False) -> Dict[str, List]:
        """
        Query memories similar to the given text.
        
        Args:
            query_text: The query text
            n_results: Number of results to return
            where: Metadata filter (ChromaDB where clause)
            emotion_boost: If True, boost results with higher emotion weights
            
        Returns:
            Dictionary with 'ids', 'documents', 'metadatas', and 'distances'
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode_query(query_text)
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            where=where
        )
        
        # Apply emotion weighting if requested
        if emotion_boost:
            results = self._apply_emotion_boost(results)
        
        return results
    
    def _apply_emotion_boost(self, results: Dict[str, List]) -> Dict[str, List]:
        """
        Re-rank results based on emotion weights.
        
        Args:
            results: Query results from ChromaDB
            
        Returns:
            Re-ranked results
        """
        if not results['ids'] or not results['ids'][0]:
            return results
        
        # Extract data from nested lists
        ids = results['ids'][0]
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]
        
        # Calculate emotion-weighted scores
        scored_results = []
        for i in range(len(ids)):
            emotion = metadatas[i].get('emotion', 0.5)
            distance = distances[i]
            
            # Lower distance is better, so we use (1 - distance) as similarity
            # Boost by emotion weight (higher emotion = more important)
            emotion_weight = 1.0 + (emotion * 0.5)  # Boost up to 50% more
            weighted_score = (1.0 - distance) * emotion_weight
            
            scored_results.append({
                'id': ids[i],
                'document': documents[i],
                'metadata': metadatas[i],
                'distance': distance,
                'score': weighted_score
            })
        
        # Sort by weighted score (higher is better)
        scored_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Reconstruct results dictionary
        return {
            'ids': [[r['id'] for r in scored_results]],
            'documents': [[r['document'] for r in scored_results]],
            'metadatas': [[r['metadata'] for r in scored_results]],
            'distances': [[r['distance'] for r in scored_results]]
        }
    
    def delete_memory(self, memory_id: str):
        """Delete a memory by ID."""
        self.collection.delete(ids=[memory_id])
    
    def get_memory(self, memory_id: str) -> Optional[Dict]:
        """
        Get a specific memory by ID.
        
        Args:
            memory_id: The memory ID
            
        Returns:
            Dictionary with memory data or None if not found
        """
        results = self.collection.get(ids=[memory_id])
        
        if results['ids'] and len(results['ids']) > 0:
            return {
                'id': results['ids'][0],
                'document': results['documents'][0],
                'metadata': results['metadatas'][0]
            }
        
        return None
    
    def count(self) -> int:
        """Get the total number of memories stored."""
        return self.collection.count()
    
    def clear(self):
        """Clear all memories from the collection."""
        # Delete and recreate collection
        self.client.delete_collection(name=self.collection_name)
        self.collection = self._get_or_create_collection()
