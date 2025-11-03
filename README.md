# Orion: Persistence of Vision

Orion is a Python framework for building local AI assistants with persistent memory. Built on text-generation-webui integration, ChromaDB for long-term storage, and intfloat/e5-large-v2 embeddings, Orion enables RAG (Retrieval-Augmented Generation) with emotion-weighted context. Designed for creators building intelligent, memory-enabled AI assistants.

## 🌟 Features

- **Long-Term Memory**: Persistent storage using ChromaDB with semantic search
- **Emotion-Weighted Context**: Prioritize emotionally significant memories in retrieval
- **Pooled Memory Storage**: Batch insert multiple memories efficiently
- **RAG Integration**: Automatic context retrieval and injection into prompts
- **Modular Architecture**: Easy to extend and customize components
- **YAML Configuration**: Simple, declarative configuration management
- **CLI Interface**: Command-line tools for memory management and chat
- **text-generation-webui Integration**: Seamless LLM API connectivity

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/DigitalMith/orion-persistence-of-vision.git
cd orion-persistence-of-vision

# Install dependencies
pip install -r requirements.txt

# Install Orion
pip install -e .
```

### Initialize Configuration

```bash
orion init-config
```

### Start Chatting

```bash
# Interactive mode
orion chat

# Single prompt
orion chat --prompt "Tell me about AI"
```

## 📖 Usage

### CLI Commands

```bash
# Memory management
orion add-memory "User prefers Python" --emotion 0.7
orion query "programming languages" --n-results 5
orion stats

# Chat
orion chat
orion chat --prompt "Hello!" --no-memory
```

### Python API

```python
from orion.core.assistant import OrionAssistant

# Initialize assistant
assistant = OrionAssistant()

# Add memories with emotion weights
assistant.add_memory("User loves hiking", emotion=0.8)

# Pooled memory storage
assistant.add_memories(
    texts=["Memory 1", "Memory 2", "Memory 3"],
    emotions=[0.6, 0.7, 0.9]
)

# Query with emotion boost
results = assistant.query_memory(
    "outdoor activities",
    n_results=5,
    emotion_boost=True
)

# Generate with RAG context
response = assistant.generate_with_context(
    "What should I do this weekend?",
    use_memory=True
)
```

## 🏗️ Architecture

```
orion/
├── core/
│   ├── config.py          # YAML configuration loader
│   ├── embeddings.py      # E5 embedding model wrapper
│   ├── memory.py          # ChromaDB memory manager
│   ├── retrieval.py       # RAG retriever
│   ├── llm_client.py      # text-generation-webui client
│   └── assistant.py       # Main assistant class
├── cli.py                 # Command-line interface
└── utils/                 # Utility modules
```

## ⚙️ Configuration

Create `config/orion.yaml`:

```yaml
embedding:
  model: intfloat/e5-large-v2

memory:
  database: ./chroma_data
  collection: orion_memory

retrieval:
  n_results: 5
  emotion_boost: true
  context_template: "Relevant memories:\n{memories}\n\n"

llm:
  url: http://localhost:5000
  api_key: null
```

## 📚 Documentation

See [USAGE.md](USAGE.md) for detailed documentation and examples.

## 🎯 Key Concepts

### Emotion-Weighted Context

Assign emotion weights (0.0 to 1.0) to memories. Higher weights indicate more emotionally significant content, which is prioritized during retrieval.

```python
assistant.add_memory("User was excited about new project", emotion=0.9)
assistant.add_memory("User mentioned routine task", emotion=0.2)
```

### Pooled Memory Storage

Efficiently store multiple memories at once:

```python
assistant.add_memories(
    texts=["Memory 1", "Memory 2", "Memory 3"],
    emotions=[0.6, 0.7, 0.9],
    metadatas=[{'type': 'fact'}, {'type': 'preference'}, {'type': 'event'}]
)
```

### RAG Retrieval

Automatically retrieve relevant context and inject into prompts:

```python
# Context is automatically retrieved and added to the prompt
response = assistant.generate_with_context(
    "What are my interests?",
    use_memory=True
)
```

## 🔧 Requirements

- Python 3.8+
- ChromaDB 0.4.0+
- sentence-transformers 2.2.0+
- PyTorch 2.0.0+
- text-generation-webui (for LLM generation)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with [ChromaDB](https://www.trychroma.com/)
- Embeddings by [intfloat/e5-large-v2](https://huggingface.co/intfloat/e5-large-v2)
- LLM integration via [text-generation-webui](https://github.com/oobabooga/text-generation-webui)
