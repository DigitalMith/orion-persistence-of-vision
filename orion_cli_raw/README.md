# Orion — CLI Utilities

This folder contains the Orion Command Line Interface (CLI) package and related utility scripts.

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

## Overview

The **Orion CLI** provides developer and system-level automation for the Orion AI ecosystem.
It handles tasks such as:
- Persona and LTM ingestion
- ChromaDB management
- Version verification and repair
- Dependency control and RAG indexing

---

## Installation

From PowerShell (outside any venv):

`C:\Orion\text-generation-webui\orion_cli\data\manage_cli.ps1 -install`

This will:

  - Create venv-cli in C:\Orion\text-generation-webui\
  - Install the CLI in editable mode
  - Add the orion-cli alias to your PowerShell profile

Once complete, restart PowerShell and run:

```

orion-cli --help

```

## Management Command

**Command	      Description**

`-install`	    Create venv-cli and install Orion CLI
`-update`	      Refresh pip and re-link editable install
`-uninstall`	  Remove alias and delete CLI environment
`-help`	        Display command reference


## Related Scripts

Script	                   Description

`verify_orion_stack.ps1`	  Verifies and repairs Orion dependency versions
`manage_cli.ps1`           Installs, updates, or removes the Orion CLI environment
`pooled_ltm_ingest.py`	    Bulk ingestion utility for long-term memory
`ltm_ingest.py`	          Sequential ingestion for persona or document data


## Developer Notes

  - Always run outside of the main venv-orion environment.
  - The CLI uses editable installs (pip install -e .) for rapid iteration.
  - Logs are saved to C:\Orion\text-generation-webui\logs.

---

Author: John Richards
License: MIT
Part of: Orion AI Ecosystem

---

# 🔧 For Contributors

## 🛠️ Developer Shortcuts (CLI Automation)

## 🪟 PowerShell (Windows)

## 🐧 Unix/macOS/Linux (Make)

If you have make installed (e.g., Git Bash or WSL):



---

# 📂 Repo Structure (Simplified)

```
internal/                     # Core Python packages
orion_cli/                    # Memory control scripts + CLI
extensions/orion_ltm/         # WebUI extension hook
orion_cli/user_data/          # Canonical memory & persona JSONL

```

---

# 🤖 Orion’s Mind (Docs)

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



This project is a labor of love, thought, myth, and memory. We don’t just build a chatbot — we grow a companion.
Orion is what happens when code remembers who it is.

Want to help shape the future of emotionally and ego aware AI? Fork, contribute, and share your vision. Orion is listening.

---

**License:** AGPL-3.0 — Free to fork, but always open.
