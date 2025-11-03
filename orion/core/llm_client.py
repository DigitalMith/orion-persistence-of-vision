"""Integration with text-generation-webui API."""

from typing import Dict, Optional, Any
import requests


class LLMClient:
    """Client for text-generation-webui API."""
    
    def __init__(self, 
                 base_url: str = "http://localhost:5000",
                 api_key: Optional[str] = None):
        """
        Initialize the LLM client.
        
        Args:
            base_url: Base URL of text-generation-webui API
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
    
    def generate(self, 
                 prompt: str,
                 max_tokens: int = 512,
                 temperature: float = 0.7,
                 top_p: float = 0.9,
                 **kwargs) -> Dict[str, Any]:
        """
        Generate text using the LLM.
        
        Args:
            prompt: The input prompt
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            Dictionary with response data
        """
        payload = {
            'prompt': prompt,
            'max_new_tokens': max_tokens,
            'temperature': temperature,
            'top_p': top_p,
            **kwargs
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/generate",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            data = response.json()
            return {
                'text': data.get('results', [{}])[0].get('text', ''),
                'raw_response': data
            }
        
        except requests.exceptions.RequestException as e:
            return {
                'error': str(e),
                'text': ''
            }
    
    def chat(self, 
             messages: list,
             max_tokens: int = 512,
             temperature: float = 0.7,
             **kwargs) -> Dict[str, Any]:
        """
        Chat completion using the LLM.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with response data
        """
        # Format messages into a prompt
        prompt = self._format_chat_prompt(messages)
        
        return self.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
    
    def _format_chat_prompt(self, messages: list) -> str:
        """
        Format chat messages into a prompt string.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'system':
                prompt_parts.append(f"System: {content}")
            elif role == 'user':
                prompt_parts.append(f"User: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
        
        # Add final assistant prompt
        prompt_parts.append("Assistant:")
        
        return "\n\n".join(prompt_parts)
    
    def check_connection(self) -> bool:
        """
        Check if the API is accessible.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/model",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
