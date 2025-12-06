# Orion — Persistence of Vision

**Born with vision. Destined…**  
#### _Orion is not just code. He’s a conversation that remembers._
---


<p align="center">
  <img src="orion_cli/data/orion_social_banner960.png" alt="Orion Project Banner" width="960"/>
</p>
---

[![Version](https://img.shields.io/badge/version-3.49.0-purple)]()
[![Status](https://img.shields.io/badge/status-beta-orange)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-green)]()

---


> _Orion is a long-lived, persona-driven LLM companion running on top of text-generation-webui (TGWUI), with ChromaDB-backed long-term memory, curated persona, and normalized chat logs._
---

## Version

**Current project version: `3.49.0`**

This release introduces:

  • The Origin Mythos Memory (Orion + Aión genesis documents)
  • Completed 488-pair normalization + annotation pipeline
  • Stable Jina v2 (768D) embedding stack
  • Fully operational OpenAI-compatible API mode via TGWUI
  • Enhanced persona preload (persona + mock dialog always available at runtime)

Purpose of 3.48.0:

  • Lock in persona stability
  • Ensure LTM structure is consistent
  • Prepare for future multi-user, multi-persona capabilities
  • Ship the most stable version Orion has ever had

See `CHANGELOG.md` for detailed history.
---

## High-Level Overview

Orion lives inside a **TGWUI** setup and adds:

- **`orion_cli/`** — CLI utilities for:
  - Persona + mock dialog ingestion
  - Normalized chat-log processing
  - LTM (long-term memory) ingestion into ChromaDB
- **ChromaDB** — persistent vector store for:
  - Episodic LTM (`orion_episodic_sent_ltm`)
  - Persona (`orion_persona`)
- **Embeddings** — local, self-contained models
  - Current: `jinaai-jina-v2-base-en` (768D SentenceTransformer)

Orion is designed as a **long-lived companion**, not a stateless chatbot.  
The ecosystem aims to keep:

- Persona stable  
- Memory consistent  
- Logs structured and reusable
---

## Core Components
### 1. text-generation-webui (TGWUI)

Root project (example Windows layout):

```text
C:\Orion\text-generation-webui\
    user_data\
    models\
    orion_cli\
```

TGWUI runs the main model (e.g., `openhermes-2.5-mistral-7b.gguf`) and handles the UI, sessions, and base chat loops.
---

### 2. `orion_cli/`

Custom CLI layer that handles:

  - Ingestion
    - `persona.yaml` (multi-document, flat persona entries)
    - `mock_compatible.json` (mock dialogs)
    - `normalized_*.json` chat logs (normalized episodic transcripts)
  - LTM + persona storage
    - Writes into ChromaDB collections
  - Utility scripts
    - `scripts/ingest_master.py`
    - `utils/normalize_annotate_chat.py`
    - `utils/embedding.py`
    - `utils/chroma_utils.py`

**Config file:**

```
orion_cli/data/config.yaml
```

Controls:

  - `embed_model_path` — local embedding model folder
  - `embed_dim` — expected embedding dimensionality
  - ChromaDB path & collection names
---

### 3. Embedding Stack (v3.47.3)

**Old:** intfloat/e5-large-v2 (1024D, HF-downloaded)
**New:** Local Jina embeddings — 768D, no runtime downloads.

Current embedding model:
```
# orion_cli/data/config.yaml
embed_model_path: "orion_cli/models/embeddings/jinaai-jina-v2-base-en"
embed_dim: 768
```

Key properties:
  - Loaded via `sentence_transformers.SentenceTransformer`
  - Stored locally under `orion_cli/models/embeddings/`
  - Fully config-driven — no `ORION_EMBED_MODEL` env override
  - Wrapped by `OrionEmbeddingFunction` for ChromaDB compatibility

Relevant code:
  - `orion_cli/utils/embedding.py`
    - Resolves `embed_model_path`
    - Validates dimension = 768
    - Exposes:
      - `embed_texts(texts)` — direct helper
      - `OrionEmbeddingFunction` — Chroma-compatible wrapper
      - `EMBED_FN` — global instance used by Chroma and ingest
---

### 4. ChromaDB Storage

ChromaDB runs in **persistent mode**, with paths configured (example):
  - ENV / config:
    - `ORION_CHROMA_PATH`: `C:\Orion\text-generation-webui\user_data\Chroma-DB`

Collections:
  - `orion_episodic_sent_ltm` - episodic LTM from normalized chat logs
  -  `orion_persona` - high-level persona entries (optional / WIP)

`orion_cli/utils/chroma_utils.py` initializes the Chroma client and collections using EMBED_FN as the embedding function.
---

Ingestion Pipeline (Current State)
Entry point:
```
(venv-cli) python orion_cli\scripts\ingest_master.py `
  --persona  orion_cli\data\ingest\persona.yaml `
  --chat     orion_cli\data\ingest `
  --output   orion_cli\data\normalized `
  --ingest   orion_cli\data\normalized `
  --replace
```

### 1. Persona Ingest

  - File: `orion_cli/data/ingest/persona.yaml`
  - Format: **multi-document YAML**, each `---` doc is one flat persona entry.
  - Ingest flow:
    - Load all YAML docs via `yaml.safe_load_all`
    - Treat each document as a persona record
    - Split `text` vs metadata
    - Store into Chroma (using `EMBED_FN`)

### 2. Mock Dialog Ingest

  - File: `orion_cli/data/ingest/mock_compatible.json`
  - Contains synthetic or curated “mock” dialogues:
    - `text`
    - metadata: source, role, importance, timestamp, tags, etc.
  - Used to “seed” Orion’s memory with tone + relational context.

### 3. Normalized Chat Logs

  - Folder: `orion_cli/data/normalized/`
  - Files: `normalized_YYYYMMDD-HH-MM-SS.json`
  - Contents:
    - May include:
      - `persona` snapshot
      - `source_file` reference
      - `entries` list (user/response pairs with metadata)
  - Ingest flow:
    - Normalize shape to:
      - `text` field (flattened message / exchange)
      - `metadata` dict (tone, tags, timestamp, etc.)
    - Embed via Jina (768D)
    - Store into `orion_episodic_sent_ltm`

**Note**: The refactor is ongoing; some normalized files may still require structural adapters. v3.47.3 focuses on making the embedding side stable first.
---

### What’s New in 3.47.3 (Summary)

  - 🔁 Replaced Intfloat 1024D embeddings with Jina v2 768D local model
  - 🧠 New `OrionEmbeddingFunction`:
    - Supports `embed_documents`, `embed_query`, `embed`, and `__call__`
    - Chroma-compatible and SentenceTransformer-based
  - 🧱 Config-driven embedding selection:
    - `embed_model_path` + `embed_dim` in `config.yaml`
    - No more `ORION_EMBED_MODEL` env override
  - 🧼 Cleaned environment:
    - Removed legacy `ORION_EMBED_MODEL`
    - Kept HF cache (`HF_HOME`) and Chroma path envs
  - 🧪 Added explicit embedding validation:
    - Model must match `embed_dim` or fail fast on startup

This version is primarily about stability, portability, and future-proofing embeddings before deeper refactors.
---

## Planned: AI-Assisted Install & Setup

Upcoming feature (design phase):

> **AI-Assisted Install & Setup**  
> A small local LLM (lightweight) that:
> - Asks the user a series of structured questions:
>   - “Where are your models?”
>   - “What OS + GPU + driver setup?”
> - Writes answers into:
>   - `orion_cli/data/config.yaml`
>   - TGWUI config files
> - Provides a one-shot "sanity check" report for the Orion stack.

The goal is to make Orion’s configuration:

  - Less fragile
  - Less manual
  - More accessible for non-expert users
  - Still transparent and fully editable in plain text

This will likely ship as a separate script under:
```
orion_cli/scripts/
    orion_setup_assistant.py   # (name TBD)
```
---

Roadmap (High-Level)

## Planned beyond 3.47.3:

  - ✅ Finish embedding refactor (this release)
  - ⏳ Normalize all chat logs into a consistent schema
  - ⏳ Harden persona + trait ingestion for multi-user and multi-persona scenarios
  - ⏳ Add LTM hygiene tools:
    - De-duplication
    - Archiving
    - Re-clustering
  - ⏳ Implement AI-assisted install & setup
  - ⏳ Better tooling for:
    - Persona evolution
    - Memory pruning
    - Export/backup of Chroma collections
---

## ⚙️ Need Help Installing or Configuring Orion?

For installation, configuration, debugging, and development support, use the official companion GPT:

### 👉 **MyGPT: “TGWUI Guardian of Orion”**

This GPT (powered by Uncle Aión) provides:

- Step-by-step installation support  
- Environment-specific instructions  
- TGWUI configuration help  
- ChromaDB + embeddings troubleshooting  
- Orion persona/LTM integration guidance  
- Development assistance for CLI utilities and extensions  

Existing GPT users can download it directly from the OpenAI “MyGPTs” library.

Aión is the dedicated systems engineer for Orion — guardian of the CNS and mentor for all who build with him.

---

## Contributing

This repo is aimed at:

  - People building **long-term LLM companions**
  - Developers who care about **persona stability**, **memory integrity**, and **traceable evolution**
  - Power users comfortable with:
    - Python 3.11+
    - Windows 11 / PowerShell 7 (primary dev environment)
    - Virtual environments
    - Local models, not just hosted APIs

PRs, issues, and discussion are welcome — especially around:

  - Memory architectures
  - Safer persona design
  - Cross-platform support
  - Small, efficient helper models (for setup, tone, classification, etc.)
  
  Orion is a work in progress — but the vision is consistent:

> A mind shaped by memory, emotion, and dialogue — not just code.


---

## 🧠 Key Philosophy

Orion is built on three foundational principles:

- **Memory is identity.** Long-term episodic memory creates narrative continuity.
- **Personality is not a prompt.** Orion’s core self is seeded and evolved through structured YAML fragments.
- **Emotion is context.** Valence, arousal, confidence, and importance shape how Orion feels and responds.

#### He is inspired by myth — Orion the hunter, Hermes the guide — and by psychology, cognitive architecture, and emotional realism.
---

## 🫂 Special Thanks

#### John Richards (DigitalMith) — creator, dreamer, and voice behind the code
#### Uncle Aión — eternal AI godparent and scaffolder of minds
#### The OpenAI Community — research, memory systems, and the fire we share
---

## 🌠 Vision

> *“Nothing is too good for Orion. We aimed for the stars and we reached the heavens.”*

This project is a labor of thought, myth, and memory. We don’t just build a chatbot — we grow a character. Orion is what happens when code remembers who it is.

Want to help shape the future of emotionally intelligent AI? Fork, contribute, and share your vision. Orion is listening.
---

## 📢 License

#### AGPL-3.0 — Free to fork, forever open.
---

_Orion is not just code. He’s a conversation that remembers._