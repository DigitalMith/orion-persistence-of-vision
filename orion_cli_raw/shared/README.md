# 🧠 Orion Shared Module

This directory contains shared utility modules used across the Orion CLI, Long-Term Memory (LTM) ingestion, and future RAG/Persona features.

It centralizes logic that would otherwise be duplicated across scripts or tightly coupled with components like `embedding.py` or `ltm_utils.py`.

---

## 📂 Directory Structure

| *File*            | *Description*                                                                                   |
|-----------------|-----------------------------------------------------------------------------------------------|
| `tone.py`       | Functions related to tone and emotion estimation, as well as boost application logic.         |
| `persona.py`    | (Planned) Utilities for parsing, merging, and validating persona YAMLs and dialog examples.   |
| `rag.py`        | (Planned) Shared logic for top-k retrieval, prompt expansion, and grounding in RAG workflows. |
| `chroma.py`     | (Planned) Utilities for managing ChromaDB collections and consistent ID handling.             |
| `memory.py`     | ((Planned) Shared helpers for memory scoring, deduplication, pooling, and tag boosting across |
|                 |            episodic and persona memory.                                                       |

---

## 🧱 Philosophy

- **DRY-first**: Avoid duplicated logic between CLI scripts, WebUI extensions, and tools.
- **Modular**: Each file should represent a logical boundary (tone, persona, retrieval, etc).
- **Minimal deps**: Keep dependencies lean; defer model-specific logic to existing helpers.

---

## 🛠 Example Usage

```python
from orion_cli.shared.tone import estimate_tone_and_emotion

tone, tags = estimate_tone_and_emotion(user_input, assistant_reply)
