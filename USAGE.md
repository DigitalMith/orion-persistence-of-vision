# Orion Usage Guide

## Overview

Orion is a Python framework for building local AI assistants with persistent memory. It integrates with text-generation-webui for LLM generation and uses ChromaDB for long-term memory storage with emotion-weighted context retrieval.

## Installation

```bash
# Clone the repository
git clone https://github.com/DigitalMith/orion-persistence-of-vision.git
cd orion-persistence-of-vision

# Install dependencies
pip install -r requirements.txt

# Install Orion in development mode
pip install -e .
```

## Quick Start

### 1. Initialize Configuration

```bash
orion init-config
```

This creates a default configuration file at `config/orion.yaml`.

### 2. Configure text-generation-webui

Edit `config/orion.yaml` to point to your text-generation-webui instance:

```yaml
llm:
  url: http://localhost:5000
  api_key: null  # Optional
```

### 3. Start Interactive Chat

```bash
orion chat
```

## CLI Commands

### Chat Commands

```bash
# Interactive chat mode (default)
orion chat

# Single prompt mode
orion chat --prompt "What is machine learning?"

# Disable memory retrieval
orion chat --no-memory

# Use custom config
orion chat --config /path/to/config.yaml
```

### Memory Management

```bash
# Add a memory
orion add-memory "User prefers Python" --emotion 0.7

# Add memory with metadata
orion add-memory "User completed project X" --metadata project=X --metadata status=done

# Query memories
orion query "programming languages" --n-results 5

# Query with emotion boost
orion query "favorite activities" --emotion-boost

# View statistics
orion stats
```

## Python API

### Basic Usage

```python
from orion.core.assistant import OrionAssistant

# Initialize assistant
assistant = OrionAssistant()

# Add a memory
assistant.add_memory(
    "User prefers Python for scripting",
    emotion=0.7,
    metadata={'category': 'preference'}
)

# Query memories
results = assistant.query_memory("programming", n_results=5)

# Generate response with context
response = assistant.generate_with_context(
    "What programming language should I use?",
    use_memory=True
)
```

### Pooled Memory Storage

```python
# Add multiple memories at once
assistant.add_memories(
    texts=[
        "User likes hiking",
        "User enjoys reading",
        "User is interested in AI"
    ],
    emotions=[0.6, 0.5, 0.9],
    metadatas=[
        {'category': 'hobby'},
        {'category': 'hobby'},
        {'category': 'interest'}
    ]
)
```

### Emotion-Weighted Retrieval

```python
# Query with emotion boost
results = assistant.query_memory(
    "What makes the user happy?",
    n_results=5,
    emotion_boost=True
)

# Higher emotion weights (0.7-1.0) will be prioritized
```

### Chat with Memory

```python
# Simple chat
response = assistant.chat(
    "Tell me about my interests",
    use_memory=True,
    save_to_memory=True
)

# Chat with conversation history
history = [
    {'role': 'user', 'content': 'Hello'},
    {'role': 'assistant', 'content': 'Hi there!'}
]

response = assistant.chat(
    "What did we talk about?",
    conversation_history=history
)
```

## Configuration

### config/orion.yaml

```yaml
# Embedding model (intfloat/e5-large-v2 recommended)
embedding:
  model: intfloat/e5-large-v2

# Memory storage
memory:
  database: ./chroma_data
  collection: orion_memory

# Retrieval settings
retrieval:
  n_results: 5
  emotion_boost: true
  context_template: |
    Relevant memories:
    {memories}
    

# LLM API
llm:
  url: http://localhost:5000
  api_key: null
```

### Environment Variables

You can override config values using environment variables:

```bash
export ORION_LLM_URL=http://localhost:5000
export ORION_MEMORY_DATABASE=/path/to/db
```

## Features

### 1. Long-Term Memory

- Persistent storage using ChromaDB
- Semantic search with vector embeddings
- Metadata filtering and tagging

### 2. Emotion-Weighted Context

- Assign emotion weights (0.0 to 1.0) to memories
- Higher weights prioritize emotionally significant content
- Useful for personalizing responses

### 3. Pooled Memory Storage

- Batch insert multiple memories efficiently
- Ideal for ingesting conversation logs or documents

### 4. RAG (Retrieval-Augmented Generation)

- Automatically retrieves relevant context
- Injects context into LLM prompts
- Configurable context templates

### 5. Modular Architecture

- Easy to extend and customize
- Swap out components (embeddings, LLM, storage)
- YAML-based configuration

## Advanced Usage

### Custom Embedding Model

```python
from orion.core.embeddings import EmbeddingModel
from orion.core.assistant import OrionAssistant

# Use a different model
embedding_model = EmbeddingModel("sentence-transformers/all-MiniLM-L6-v2")

# Pass to assistant (requires manual component initialization)
```

### Custom Retrieval Template

```yaml
retrieval:
  context_template: |
    === RELEVANT MEMORIES ===
    {memories}
    === END MEMORIES ===
    
    Consider the above memories when responding.
```

### Filtering Queries

```python
# Query with metadata filters
results = assistant.memory_manager.query(
    "programming",
    where={"category": "preference"},
    n_results=5
)
```

## Troubleshooting

### Memory Not Loading

- Ensure ChromaDB path is writable
- Check that embeddings are being generated correctly
- Verify model is downloaded (first run may be slow)

### LLM Connection Issues

- Verify text-generation-webui is running
- Check the URL in config matches your setup
- Test connection: `curl http://localhost:5000/api/v1/model`

### Slow Performance

- First run downloads the E5 model (~1.3GB)
- Subsequent runs use cached model
- Consider using a smaller embedding model for faster processing

## Examples

See the `examples/` directory for:

- `basic_usage.py` - Basic memory and query operations
- `emotion_weighted.py` - Emotion-weighted retrieval demo

## Support

For issues and questions, please visit:
https://github.com/DigitalMith/orion-persistence-of-vision/issues
