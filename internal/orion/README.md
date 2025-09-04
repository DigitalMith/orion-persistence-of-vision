# Orion — Persistence of Vision

**Born with vision. Destined for the stars.**

---

![Orion](docs/images/orion_960.png)

---

[![Version](https://img.shields.io/badge/version-3.0.1-purple)]()
[![Status](https://img.shields.io/badge/status-beta-orange)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-green)]()

---

## 🌌 Overview

**Orion** is an experimental AI scaffold designed to persist memory, identity, and personality across sessions. Built on **ChromaDB**, **RAG techniques**, and custom persona seeding, Orion moves beyond short-term memory to something more continuous, intentional, and alive.

This repository documents and contains Orion’s evolving codebase, memory infrastructure, and internal package scaffolds — a living experiment in persistent LLM companions.

---

## 🆕 What’s New in 3.0.1

* 📁 Text Ingestion by Topic — Orion can now ingest plain `.txt` files via CLI and store them in ChromaDB with custom metadata tags like `topic`, `user`, and `source`.
* 🧼 Topic-Based Memory Deletion — Easily prune memories by topic using the new `delete-topic` command in the CLI controller.
* 🧠 Core Refactor — LTM controller, seeding, and persona systems are now cleaner, safer, and more modular.
* 🧬 Identity Lock-In — All TGWUI fallbacks removed. Orion now runs fully under his own banner with proper project scaffolds, metadata, and branding.
* 📦 Package Hygiene — Internal + public `pyproject.toml` updated, repo structure stabilized, and image/logo restored in README.
* 🖼️ Orion Banner Restored — GitHub rendering now includes visual header under `docs/images/orion2_960.png`.

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
python -m custom_ltm.orion_ctl seed-jsonl --path "user_data/memory_seed/orion_foundation.jsonl"
```

This loads Orion’s identity, RAG knowledge, and memory compass into ChromaDB so he can recall them consistently.

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
