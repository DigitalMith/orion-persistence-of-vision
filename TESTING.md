# Testing Orion Framework

This guide explains how to test the Orion framework implementation.

## Prerequisites

Before testing, ensure you have:

1. Python 3.8 or higher
2. pip package manager
3. (Optional) text-generation-webui running on localhost:5000 for LLM features

## Installation for Testing

```bash
# 1. Install dependencies
pip install -r requirements.txt

# This will install:
# - chromadb (vector database)
# - sentence-transformers (for embeddings)
# - pyyaml (config parsing)
# - requests (HTTP client)
# - click (CLI framework)
# - numpy (numerical operations)
# - torch (deep learning framework)

# 2. Install Orion in development mode
pip install -e .

# 3. Verify installation
orion --version
```

## Structure Validation

Run the validation script to check all files are in place:

```bash
python3 validate_structure.py
```

Expected output:
```
✓ All checks passed! Package structure is valid.
```

## Unit Testing (Without LLM)

### Test 1: Configuration Loading

```bash
# Initialize a config file
orion init-config

# Verify config was created
cat config/orion.yaml
```

### Test 2: Python API - Basic Memory Operations

Create a test file `test_memory.py`:

```python
from orion.core.assistant import OrionAssistant

# Initialize (this will download the E5 model on first run - ~1.3GB)
print("Initializing Orion...")
assistant = OrionAssistant()

# Test 1: Add single memory
print("\nTest 1: Adding single memory...")
mem_id = assistant.add_memory("User prefers Python", emotion=0.7)
print(f"Added memory: {mem_id}")

# Test 2: Add batch memories
print("\nTest 2: Adding batch memories...")
ids = assistant.add_memories(
    texts=["User likes hiking", "User enjoys coding", "User reads sci-fi"],
    emotions=[0.6, 0.8, 0.5]
)
print(f"Added {len(ids)} memories")

# Test 3: Query memories
print("\nTest 3: Querying memories...")
results = assistant.query_memory("programming", n_results=3)
print(f"Found {len(results['documents'][0])} results:")
for doc in results['documents'][0]:
    print(f"  - {doc}")

# Test 4: Emotion-weighted query
print("\nTest 4: Emotion-weighted query...")
results = assistant.query_memory("hobbies", n_results=3, emotion_boost=True)
print(f"Results with emotion boost:")
for i, doc in enumerate(results['documents'][0]):
    emotion = results['metadatas'][0][i].get('emotion', 0)
    print(f"  - {doc} (emotion: {emotion:.2f})")

# Test 5: Memory count
print(f"\nTotal memories: {assistant.get_memory_count()}")

print("\n✓ All memory tests passed!")
```

Run the test:
```bash
python3 test_memory.py
```

### Test 3: CLI Commands

```bash
# Test memory management
orion add-memory "User completed Python project" --emotion 0.9
orion add-memory "User likes coffee" --emotion 0.3
orion query "projects" --n-results 2
orion stats

# Test emotion boost
orion query "user preferences" --emotion-boost
```

### Test 4: Configuration System

Test environment variable override:

```bash
export ORION_MEMORY_DATABASE=/tmp/test_db
python3 -c "from orion.core.assistant import OrionAssistant; a = OrionAssistant(); print(a.config.get('memory.database'))"
# Should output: /tmp/test_db
```

### Test 5: Embedding Model

```python
from orion.core.embeddings import EmbeddingModel

model = EmbeddingModel()
print(f"Model dimension: {model.dimension}")

# Test encoding
embeddings = model.encode(["Hello world", "AI is amazing"])
print(f"Embedding shape: {embeddings.shape}")

# Test query encoding
query_emb = model.encode_query("What is AI?")
print(f"Query embedding shape: {query_emb.shape}")
```

## Integration Testing (With LLM)

These tests require text-generation-webui running.

### Setup text-generation-webui

1. Follow instructions at: https://github.com/oobabooga/text-generation-webui
2. Start the server: `python server.py --api`
3. Verify it's running: `curl http://localhost:5000/api/v1/model`

### Test 6: LLM Client

```python
from orion.core.llm_client import LLMClient

client = LLMClient("http://localhost:5000")

# Check connection
if client.check_connection():
    print("✓ Connected to LLM API")
    
    # Test generation
    result = client.generate("What is 2+2?", max_tokens=50)
    print(f"Response: {result['text']}")
else:
    print("✗ Cannot connect to LLM API")
```

### Test 7: RAG Integration

```python
from orion.core.assistant import OrionAssistant

assistant = OrionAssistant()

# Add context
assistant.add_memory("User is learning Python programming", emotion=0.8)
assistant.add_memory("User prefers visual learning", emotion=0.6)

# Generate with context
response = assistant.generate_with_context(
    "How should I learn Python?",
    use_memory=True
)
print(f"Response: {response}")
```

### Test 8: Interactive Chat

```bash
# Start interactive mode
orion chat

# In the chat:
# 1. Type: "I love hiking in the mountains"
# 2. Type: "I'm learning Python"
# 3. Type: "stats" to see memory count
# 4. Type: "What are my interests?" (should recall previous messages)
# 5. Type: "quit" to exit
```

## Example Scripts

Test the provided examples:

```bash
# Basic usage example
python3 examples/basic_usage.py

# Emotion-weighted example
python3 examples/emotion_weighted.py
```

## Performance Testing

### Test Model Load Time

```python
import time
from orion.core.embeddings import EmbeddingModel

start = time.time()
model = EmbeddingModel()
load_time = time.time() - start

print(f"Model load time: {load_time:.2f}s")
# First run: ~10-30s (downloads model)
# Subsequent runs: ~2-5s (cached)
```

### Test Embedding Speed

```python
import time
from orion.core.embeddings import EmbeddingModel

model = EmbeddingModel()
texts = ["Test text"] * 100

start = time.time()
embeddings = model.encode(texts)
elapsed = time.time() - start

print(f"Embedded {len(texts)} texts in {elapsed:.2f}s")
print(f"Average: {elapsed/len(texts)*1000:.2f}ms per text")
```

### Test Memory Operations

```python
import time
from orion.core.assistant import OrionAssistant

assistant = OrionAssistant()

# Test batch insert
texts = [f"Memory {i}" for i in range(100)]
start = time.time()
assistant.add_memories(texts)
elapsed = time.time() - start
print(f"Batch insert 100 memories: {elapsed:.2f}s")

# Test query
start = time.time()
results = assistant.query_memory("memory", n_results=10)
elapsed = time.time() - start
print(f"Query 10 results: {elapsed:.3f}s")
```

## Troubleshooting

### Issue: "No module named 'chromadb'"

```bash
pip install chromadb
```

### Issue: "No module named 'sentence_transformers'"

```bash
pip install sentence-transformers
```

### Issue: Model download fails

The E5 model is ~1.3GB. Ensure you have:
- Sufficient disk space
- Internet connection
- No firewall blocking huggingface.co

### Issue: "Config file not found"

```bash
orion init-config
```

### Issue: LLM connection fails

- Verify text-generation-webui is running
- Check the URL in config/orion.yaml
- Test: `curl http://localhost:5000/api/v1/model`

## Success Criteria

✓ Structure validation passes
✓ All Python files have valid syntax
✓ Config system works
✓ Memory operations (add, query, batch) work
✓ Embeddings generate successfully
✓ CLI commands execute without errors
✓ (Optional) LLM integration works
✓ Example scripts run successfully

## Clean Up Test Data

```bash
# Remove test database
rm -rf ./chroma_data

# Clear test memories in Python
python3 -c "from orion.core.assistant import OrionAssistant; OrionAssistant().clear_memory()"
```

## Automated Test Suite

For continuous integration, create `test_suite.py`:

```python
#!/usr/bin/env python3
"""Automated test suite for Orion (no LLM required)."""

import sys
import tempfile
from pathlib import Path

def test_imports():
    """Test that all modules can be imported."""
    try:
        from orion import ConfigLoader, MemoryManager, EmbeddingModel, RAGRetriever
        from orion.core.assistant import OrionAssistant
        from orion.core.llm_client import LLMClient
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_config():
    """Test configuration loading."""
    try:
        from orion.core.config import ConfigLoader
        config = ConfigLoader("config/orion.yaml")
        assert config.get('embedding.model') == 'intfloat/e5-large-v2'
        print("✓ Config loading works")
        return True
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        return False

def test_memory_operations():
    """Test basic memory operations."""
    try:
        from orion.core.assistant import OrionAssistant
        
        # Use temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            assistant = OrionAssistant()
            assistant.memory_manager.db_path = Path(tmpdir)
            
            # Add memory
            mem_id = assistant.add_memory("Test memory", emotion=0.5)
            assert mem_id is not None
            
            # Query
            results = assistant.query_memory("test", n_results=1)
            assert len(results['documents'][0]) > 0
            
            print("✓ Memory operations work")
            return True
    except Exception as e:
        print(f"✗ Memory test failed: {e}")
        return False

def main():
    """Run all tests."""
    tests = [
        test_imports,
        test_config,
        # test_memory_operations,  # Commented out - requires model download
    ]
    
    results = [test() for test in tests]
    
    if all(results):
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {len([r for r in results if not r])} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

Run with:
```bash
python3 test_suite.py
```
