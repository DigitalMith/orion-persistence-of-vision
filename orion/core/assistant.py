"""Main Orion Assistant class integrating all components."""

from typing import Optional, Dict, Any, List
from orion.core.config import ConfigLoader
from orion.core.embeddings import EmbeddingModel
from orion.core.memory import MemoryManager
from orion.core.retrieval import RAGRetriever
from orion.core.llm_client import LLMClient


class OrionAssistant:
    """Main Orion AI Assistant with persistent memory and RAG."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Orion Assistant.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = ConfigLoader(config_path)
        
        # Initialize components
        self._init_components()
    
    def _init_components(self):
        """Initialize all components based on configuration."""
        # Embedding model
        model_name = self.config.get('embedding.model', 'intfloat/e5-large-v2')
        self.embedding_model = EmbeddingModel(model_name)
        
        # Memory manager
        db_path = self.config.get('memory.database', './chroma_data')
        collection = self.config.get('memory.collection', 'orion_memory')
        self.memory_manager = MemoryManager(
            db_path=db_path,
            collection_name=collection,
            embedding_model=self.embedding_model
        )
        
        # RAG retriever
        retrieval_config = {
            'n_results': self.config.get('retrieval.n_results', 5),
            'emotion_boost': self.config.get('retrieval.emotion_boost', False),
            'context_template': self.config.get(
                'retrieval.context_template',
                "Relevant memories:\n{memories}\n\n"
            )
        }
        self.retriever = RAGRetriever(self.memory_manager, retrieval_config)
        
        # LLM client
        llm_url = self.config.get('llm.url', 'http://localhost:5000')
        llm_api_key = self.config.get('llm.api_key')
        self.llm_client = LLMClient(base_url=llm_url, api_key=llm_api_key)
    
    def add_memory(self, 
                   text: str,
                   metadata: Optional[Dict] = None,
                   emotion: Optional[float] = None) -> str:
        """
        Add a memory to long-term storage.
        
        Args:
            text: Memory text
            metadata: Optional metadata
            emotion: Optional emotion weight (0.0 to 1.0)
            
        Returns:
            Memory ID
        """
        return self.memory_manager.add_memory(text, metadata, emotion)
    
    def add_memories(self,
                     texts: List[str],
                     metadatas: Optional[List[Dict]] = None,
                     emotions: Optional[List[float]] = None) -> List[str]:
        """
        Add multiple memories in batch (pooled memory storage).
        
        Args:
            texts: List of memory texts
            metadatas: Optional list of metadata
            emotions: Optional list of emotion weights
            
        Returns:
            List of memory IDs
        """
        return self.memory_manager.add_memories(texts, metadatas, emotions)
    
    def query_memory(self,
                     query: str,
                     n_results: int = 5,
                     emotion_boost: bool = False) -> Dict:
        """
        Query memories similar to the given text.
        
        Args:
            query: Query text
            n_results: Number of results to return
            emotion_boost: Whether to boost by emotion weight
            
        Returns:
            Query results
        """
        return self.memory_manager.query(query, n_results, emotion_boost=emotion_boost)
    
    def generate_with_context(self,
                             prompt: str,
                             use_memory: bool = True,
                             n_memories: Optional[int] = None,
                             emotion_boost: Optional[bool] = None,
                             **llm_kwargs) -> str:
        """
        Generate a response with RAG context from memory.
        
        Args:
            prompt: User prompt
            use_memory: Whether to retrieve context from memory
            n_memories: Number of memories to retrieve
            emotion_boost: Whether to boost by emotion weight
            **llm_kwargs: Additional parameters for LLM
            
        Returns:
            Generated response text
        """
        # Build the full prompt with context
        if use_memory:
            context = self.retriever.retrieve_context(
                query=prompt,
                n_results=n_memories,
                emotion_boost=emotion_boost
            )
            full_prompt = context + prompt
        else:
            full_prompt = prompt
        
        # Generate response
        result = self.llm_client.generate(full_prompt, **llm_kwargs)
        
        if 'error' in result:
            return f"Error: {result['error']}"
        
        return result.get('text', '').strip()
    
    def chat(self,
             user_message: str,
             conversation_history: Optional[List[Dict]] = None,
             use_memory: bool = True,
             save_to_memory: bool = True,
             **llm_kwargs) -> str:
        """
        Chat with the assistant.
        
        Args:
            user_message: User's message
            conversation_history: Previous conversation messages
            use_memory: Whether to use RAG context
            save_to_memory: Whether to save this interaction to memory
            **llm_kwargs: Additional LLM parameters
            
        Returns:
            Assistant's response
        """
        # Retrieve relevant memories if enabled
        context = ""
        if use_memory:
            context = self.retriever.retrieve_context(query=user_message)
        
        # Build messages
        messages = []
        
        if context:
            messages.append({
                'role': 'system',
                'content': f"You are Orion, an AI assistant with long-term memory. {context}"
            })
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current message
        messages.append({
            'role': 'user',
            'content': user_message
        })
        
        # Generate response
        result = self.llm_client.chat(messages, **llm_kwargs)
        response = result.get('text', '').strip()
        
        # Save to memory if enabled
        if save_to_memory and response:
            # Save user message
            self.add_memory(
                f"User: {user_message}",
                metadata={'type': 'user_message'}
            )
            # Save assistant response
            self.add_memory(
                f"Assistant: {response}",
                metadata={'type': 'assistant_message'}
            )
        
        return response
    
    def get_memory_count(self) -> int:
        """Get the total number of memories stored."""
        return self.memory_manager.count()
    
    def clear_memory(self):
        """Clear all memories."""
        self.memory_manager.clear()
