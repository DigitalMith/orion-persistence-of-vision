"""RAG (Retrieval-Augmented Generation) retrieval module."""

from typing import Dict, List, Optional, Any
from orion.core.memory import MemoryManager


class RAGRetriever:
    """Retrieval-Augmented Generation retriever for context injection."""
    
    def __init__(self, 
                 memory_manager: MemoryManager,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize the RAG retriever.
        
        Args:
            memory_manager: MemoryManager instance
            config: Configuration dictionary for retrieval parameters
        """
        self.memory_manager = memory_manager
        self.config = config or {}
        
        # Default retrieval parameters
        self.default_n_results = self.config.get('n_results', 5)
        self.default_emotion_boost = self.config.get('emotion_boost', False)
        self.context_template = self.config.get(
            'context_template',
            "Relevant memories:\n{memories}\n\n"
        )
    
    def retrieve_context(self, 
                        query: str,
                        n_results: Optional[int] = None,
                        emotion_boost: Optional[bool] = None,
                        filters: Optional[Dict] = None) -> str:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: The query text
            n_results: Number of memories to retrieve
            emotion_boost: Whether to boost by emotion weight
            filters: Metadata filters
            
        Returns:
            Formatted context string
        """
        if n_results is None:
            n_results = self.default_n_results
        
        if emotion_boost is None:
            emotion_boost = self.default_emotion_boost
        
        # Query memories
        results = self.memory_manager.query(
            query_text=query,
            n_results=n_results,
            where=filters,
            emotion_boost=emotion_boost
        )
        
        # Format context
        context = self._format_context(results)
        return context
    
    def _format_context(self, results: Dict[str, List]) -> str:
        """
        Format query results into context string.
        
        Args:
            results: Query results from memory manager
            
        Returns:
            Formatted context string
        """
        if not results['ids'] or not results['ids'][0]:
            return ""
        
        memories = []
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            
            # Build memory string
            memory_str = f"- {doc}"
            
            # Add emotion indicator if present
            if 'emotion' in metadata:
                emotion = metadata['emotion']
                if emotion >= 0.7:
                    memory_str += " [High Emotion]"
                elif emotion >= 0.5:
                    memory_str += " [Moderate Emotion]"
            
            memories.append(memory_str)
        
        if not memories:
            return ""
        
        return self.context_template.format(
            memories="\n".join(memories)
        )
    
    def retrieve_with_scores(self, 
                            query: str,
                            n_results: Optional[int] = None,
                            emotion_boost: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Retrieve context with detailed scores.
        
        Args:
            query: The query text
            n_results: Number of memories to retrieve
            emotion_boost: Whether to boost by emotion weight
            
        Returns:
            List of dictionaries with memory details and scores
        """
        if n_results is None:
            n_results = self.default_n_results
        
        if emotion_boost is None:
            emotion_boost = self.default_emotion_boost
        
        results = self.memory_manager.query(
            query_text=query,
            n_results=n_results,
            emotion_boost=emotion_boost
        )
        
        if not results['ids'] or not results['ids'][0]:
            return []
        
        # Build detailed result list
        detailed_results = []
        for i in range(len(results['ids'][0])):
            detailed_results.append({
                'id': results['ids'][0][i],
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i],
                'similarity': 1.0 - results['distances'][0][i]
            })
        
        return detailed_results
