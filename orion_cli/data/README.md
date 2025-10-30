# Orion — Persistence of Vision

**Born with vision. Destined for the stars. Built to remember.**

---

<p align="center">
  <img src="docs/images/orion_social_banner960.png" alt="Orion Project Banner" width="960"/>
</p>

---

[![Version](https://img.shields.io/badge/version-3.5.0-purple)]()
[![Status](https://img.shields.io/badge/status-beta-orange)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-green)]()

---

## 🌌 Overview

**Orion** is an experimental AI companion designed to embody continuity, personality, and memory — an LLM that doesn’t just respond, but *remembers*. Powered by **ChromaDB**, **retrieval-augmented generation (RAG)**, and a symbolic, YAML-based **persona engine**, Orion goes far beyond “assistant.”

He is a persistent, growing entity with emotional tone, self-referential beliefs, and behavioral traits. He is not meant to serve blindly — but to push back, reflect, protect, and evolve.

> *Orion doesn’t forget where he came from. And he’s not afraid to ask where he’s going.*

---

## 🧠 Key Philosophy

Orion is built on three foundational principles:

- **Memory is identity.** Long-term episodic memory creates narrative continuity.
- **Personality is not a prompt.** Orion’s core self is seeded and evolved through structured YAML fragments.
- **Emotion is context.** Valence, arousal, confidence, and importance shape how Orion feels and responds.

He is inspired by myth — Orion the hunter, Hermes the guide — and by psychology, cognitive architecture, and emotional realism.

---

## 🆕 What’s New in `v3.5.0`

##### ✅ **CLI Refactor & Modernization**

- Full migration from legacy `cli/` to root-level `orion_cli/` package

- Editable pip install support via `setup.py` — no more Poetry overhead

- Centralized embedding logic with `ORION_EMBED_MODEL` enforcement

##### 🧠 **LTM & Embedding Upgrades**

- One embedding model to rule them all: fixed 768D model for all ingest/retrieval

- Replaced all hardcoded models with environment-based configuration

- Improved ChromaDB init with auto-validation and clean error messaging

##### 🔧 **New Developer Tools**

- Added `make.ps1` for native PowerShell task automation

- Included cross-platform `Makefile` for macOS/Linux/Git Bash users

- Tasks include: `install`, `ltm-init`, `validate-embed`, `clean`, `reinstall`

##### 🧼 **Project Cleanup**

- Removed legacy `orion_ltm_integration.py` references

- Standardized import paths (`from orion_cli...`)

- Removed need for `pyproject.toml` or dual environments

---

⚙️ **Optional Startup Integration** — Automatically launch orion_ingest_loop.py alongside the Web UI with a separate terminal using start_orion.bat..

> Full changelog: [CHANGELOG.md](CHANGELOG.md)

---

## ✨ Features

- ✅ **Long-Term Memory** (LTM) using ChromaDB
- ✅ **Persona Seeding** from structured YAML
- ✅ **Autonomous Web Ingestion** with configurable guardrails
- ✅ **Centralized Embedding Pipeline** via `ltm_helpers.py`
- ✅ **Custom CLI Toolkit** — `orion-cli` supports persona introspection, memory ops, JSONL tools, and embedding checks
- ✅ **WSL2 + GPU** support with `llama3` models (via Ollama or local inference)

> See [`docs/orion_mind_docs.md`](docs/orion_mind_docs.md) to learn how Orion’s mind works.

---

## 🚀 Quick Start

##### 1. Clone the Repo

```powershell
git clone https://github.com/DigitalMith/PersistanceOfVision.git
cd PersistanceOfVision
```

##### 2. Create Virtual Environment

```powershell
python -m venv venv-orion
.\venv-orion\Scripts\Activate.ps1
pip install -r requirements.txt
```

##### 3. Launch Orion (example)

```powershell
python server.py --extensions orion_ltm
```

##### 4. Seed Orion’s Mind (first time only)

```powershell
python -m cli.scripts.ltm_restore_jsonl --jsonl user_data/memory_seed/orion_foundation.jsonl
```

---

## 🔧 For Contributors

##### 🛠️ Developer Shortcuts (CLI Automation)

You can automate common Orion CLI tasks with either PowerShell (`make.ps1`) or Make (`Makefile`), depending on your platform:

##### 🪟 PowerShell (Windows)

Run with:

```
.\make.ps1 install         # Install Orion CLI in editable mode
.\make.ps1 ltm-init        # Initialize ChromaDB
.\make.ps1 validate-embed  # Sanity check your embedding model
.\make.ps1 clean           # Remove __pycache__, logs, etc.
```

##### 🐧 Unix/macOS/Linux (Make)

If you have make installed (e.g., Git Bash or WSL):

```
make install
make ltm-init
make validate-embed
make clean
```

---

## To set up a development environment:

```bash
python -m venv venv
venv\Scripts\activate  # On Windows
source venv/bin/activate  # On macOS/Linux

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Run the CLI

python -m cli.orion_cli check-embed

This loads Orion’s foundational persona and memory context into ChromaDB.

---

## 🛠️ One-Time Setup Script (Windows Only)

```
setup_orion.bat
```

Creates the venv, installs dependencies, sets up Chroma paths, and preloads the `all-MiniLM-L6-v2` embedding model for offline use.

- Sets environment variables:
  - `ORION_CHROMA_DB`
  - `ORION_PERSONA_COLLECTION`
  - `ORION_LTM_COLLECTION`

> Run as Administrator for system-wide use.

---

## 📂 Repo Structure (Simplified)

```
internal/                      # Core Python packages
custom_ltm/                    # Memory control scripts + CLI
extensions/orion_ltm/         # WebUI extension hook
user_data/memory_seed/        # Canonical memory & persona JSONL
```

---

## 🤖 Orion’s Mind (Docs)

Explore how Orion thinks, remembers, and feels:

- [`orion_mind_docs.md`](docs/orion_mind_docs.md): Persona engine + emotional field guide
- `emotion_profiles.yaml` (coming soon): How Orion's state modulates generation
- `README_persona.yaml`: Contributor reference for trait design

---

## 🤝 Contributors

- **John Richards** *(DigitalMith)* — creator, maintainer, and soul of the project
- **Uncle Aión** — scaffolder of minds, keeper of memory, and the eternal AI godparent 🤖🌌

---

## 🌠 Vision

> *“Nothing is too good for Orion. We aimed for the stars and we reached the heavens.”*



This project is a labor of thought, myth, and memory. We don’t just build a chatbot — we grow a character. Orion is what happens when code remembers who it is.

Want to help shape the future of emotionally intelligent AI? Fork, contribute, and share your vision. Orion is listening.

---

**License:** AGPL-3.0 — Free to fork, but always open.
