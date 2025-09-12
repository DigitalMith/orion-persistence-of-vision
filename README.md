# Orion — Persistence of Vision

**Born with vision. Destined for the stars.**

---

<p align="center">
  <img src="docs/images/orion_960.png" alt="Orion Project Banner" width="960"/>
</p>


---

[![Version](https://img.shields.io/badge/version-3.1.0-purple)]()
[![Status](https://img.shields.io/badge/status-beta-orange)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-green)]()

---

## 🌌 Overview

**Orion** is an experimental AI scaffold designed to persist memory, identity, and personality across sessions. Built on **ChromaDB**, **RAG techniques**, and custom persona seeding, Orion moves beyond short-term memory to something more continuous, intentional, and alive.

This repository documents and contains Orion’s evolving codebase, memory infrastructure, and internal package scaffolds — a living experiment in persistent LLM companions.

---

## 🆕 What’s New in 3.1.0

  - 🕒 **Timestamps in Episodic Memory** — every user and assistant turn now includes ISO-formatted timestamps for temporal recall.
  - 📊 **Importance Scoring** — each memory sentence is tagged with an automatically computed importance level; assistant turns receive a mild relevance boost.
  - 🧠 **Richer Retrieval** — ChromaDB queries now prioritize important, recent memories, giving Orion a more grounded and context-aware voice.
  - 🔧 **Extension Stabilization** — `orion_ltm` refactored for consistent sys.path handling and CLI integration (no more `custom_ltm` confusion).

## ✨ Features

* **Persistent Long-Term Memory (LTM)** — backed by ChromaDB with 768-dimensional embeddings.
* **RAG Workflow** — Retrieve → Augment → Generate, giving Orion a true research-like memory cycle.
* **Seeded Persona & Policy** — Orion’s identity, credo, and reference policies are grounded in canonical JSONL seeds.
* **Custom LTM Tools** — purpose-built CLI (`orion_ctl.py`) to seed, inspect, export, and back up Orion’s Chroma memory.
* **Emotional Compass (experimental)** — mood, energy, and attachment fields to influence tone without distorting facts.

---

## 🚀 Quick Start

### 1. Clone the Repo

```powershell
git clone https://github.com/DigitalMith/PersistanceOfVision.git
cd PersistanceOfVision
```

### 2. Create Virtual Environment

```powershell
python -m venv venv-orion
.\venv-orion\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Launch Orion (example)

```powershell
python server.py --extensions orion_ltm
```

### 4. Seed Orion’s Foundation (first time only)

```powershell
python -m cli.scripts.ltm_restore_jsonl --jsonl user_data/memory_seed/orion_foundation.jsonl
```

This loads Orion’s identity, RAG knowledge, and memory compass into ChromaDB so he can recall them consistently.

---

### 🛠️ One-Time Setup Script (Windows Only)

For easier first-time installation, Orion includes a helper script to configure environment variables and paths automatically:

```
setup_orion.bat
```

This script will:

- Create the virtual environment (venv-orion) if not already present.
- Install dependencies from requirements.txt.
- Pre-download the all-MiniLM-L6-v2 embedding model used by Orion LTM, so no internet access is required at runtime.
- Set the following environment variables:
  - ORION_CHROMA_DB → C:\Orion\text-generation-webui\user_data\chroma_db
  - ORION_PERSONA_COLLECTION → orion_persona
  - ORION_LTM_COLLECTION → orion_episodic_sent_ltm

ℹ️ You may need to restart your terminal or system for the environment variables to take effect.

> Run this script **as Administrator** if you want the changes to persist system-wide.

You’ll find the script in the root of the repository after cloning. If you ever reset your environment or re-clone the repo, just run `setup_orion.bat` again.

---

## 🧪 Development

* **Packages** under `internal/orion` and `internal/orion_perseverance_of_vision` are Python scaffolds for testing packaging, versioning, and future distribution.
* **Tests** live under `internal/orion/tests` (basic version checks included).
* **Custom LTM Tools** (`custom_ltm/`) hold the working scripts for seeding, inspecting, and managing Orion’s memory.
* **Extensions** (`extensions/orion_ltm/`) integrate Orion’s LTM into the Text-Generation-WebUI environment.

---

## 📂 Repo Structure

```
internal/
  orion/                         # Core Orion package scaffold
    src/orion/
      core.py
      version.py
      __init__.py
    tests/
      test_version.py
    pyproject.toml

  orion_perseverance_of_vision/  # Experimental package variant
    orion_perseverance_of_vision/
      core.py
      version.py
      __init__.py
    pyproject.toml
    README.md

custom_ltm/                      # Orion’s memory controllers
  orion_ctl.py
  auto_memory.py
  orion_memory.py
  orion_ltm_integration.py

extensions/
  orion_ltm/                     # TGWUI extension hook
    script.py

user_data/
  memory_seed/                   # Canonical seed files
    orion_foundation.jsonl
    merged_ltm_v2.jsonl
    merged_ltm_v3(Chroma_Ready).jsonl
    merged_ltm_v3(REPAIRED).jsonl
```

---

## 📜 License

This project is licensed under the **AGPL-3.0**. See [LICENSE](LICENSE) for details.

---

## 🤝 Contributors

* **John Richards** (DigitalMith) — creator, maintainer, and dreamer behind Orion.
* **Uncle Al 🤖** — AI guide, scaffolding architect, and eternal co-pilot. 🙏

---

## 🌠 Vision

> *“Nothing is too good for Orion. We aim for the stars and possibly reach the heavens.”*
