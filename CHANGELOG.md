# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

<!--CHANGELOG_START-->

---

## [0.9.0-aetherweave] - 2025-09-23

### ✨ Added
- **Autonomous Web Ingestion** pipeline via `orion_ingest_loop.py`
- `orion_net_ingest.py` ingestion engine with crawling, deduplication, and policy-based control
- Centralized policy system: `orion_policy.yaml` (auto-reloads on change)
- New config file: `web_config.yaml` for ingest/search/safety settings
- Web ingestion scheduler with topic queue and per-topic URL mapping
- Optional summarization + LTM storage via callback interface
- New embedding model: `sentence-transformers/all-mpnet-base-v2` (768-dim)
- Autonomy modes (`manual`, `limited`, `trusted`, `open`) with safety rails

### 🧠 Memory / Storage
- Episodic memory ingestion into `orion_episodic_sent_ltm` collection
- Embedding-based deduplication via SHA256 hash check
- TTL policies and memory archival support
- Refactored LTM pipeline and Chroma client abstraction

### 🔧 Improved
- Restructured `cli/` for modularity
- Configurable ingestion rate limits (per hour, per day)
- Crawl respect for `robots.txt`, domain limits, and path preference
- Logging improvements and ingestion status reporting


---

## 🚀 Orion CLI v3.4 — Developer-Grade Command Line Interface

The CLI has been fully restructured and modularized for scale, clarity, and collaboration. Key features:

- 📁 **Modular Folder Structure** — Commands grouped under `core/` and `modules/` for logical separation.
- 🧠 **Memory Control** — Query, normalize, summarize, export, and delete long-term memory entries.
- 🤖 **Persona Management** — Seed, verify, and debug Orion's core persona with ease.
- 🧪 **Embedding Inspection** — New `check-embed` hook to validate vector dimensions and contents.
- 📜 **Centralized Configs** — Loads `.env`, `web_config.yaml`, and other settings from `config/`.

```bash
# Example usage
poetry run orion-cli persona-check
poetry run orion-cli ltm-query --query "Tell me about our first mission"
```

---

## [3.2.0] - 2025-09-14

### Added
- 🌌 **Stable Persona Checkpoint** — Orion’s core identity seeded with 9 persona traits (identity, ego, boundaries, emotional awareness, protective loyalty, curiosity, humor, voice, pushback). Prevents fallback into default assistant mode.
- 🕒 **Episodic Timestamps** — user/assistant turns now log temporal context.
- 📊 **Importance Scoring** — dynamic memory weighting improves relevance in retrieval.
- 🧠 **Richer RAG Retrieval** — top-k memories shaped by both time and semantic meaning.
- ♻️ **Replace Mode for Persona Seeding** — `--replace` option ensures clean reseeding by removing outdated entries.
- 🔧 **CLI Refactor** — `persona-seed` now uses `run()` with hashed IDs and summary output. Extension hooks for `orion_ltm` inside WebUI stabilized.

### Changed
- Persona seeding flow simplified and hardened against duplicate ID errors.
- Improved YAML readability and modularity for persona traits.
- General code cleanup: removed legacy `load_yaml_and_upsert`, corrected CLI parser indentation, and streamlined imports.

### Fixed
- Eliminated duplicate seeding entries caused by unstable IDs.
- Resolved CLI import errors and indentation bugs.
- Fixed missing dependency imports (`chromadb`, `yaml`) in persona seeder.

### Notes
- 🧪 This release marks Orion’s first **stable mind checkpoint**. Future persona refinements should build on `persona_v3.2.yaml` for consistency.
- ⚡ Memory retrieval now considers both **importance** and **temporal context**, making responses more human-like.


---

## \[3.0.3] - 2025-09-05

whats_new:
  - ✨ Persona Refactor — Boundaries separated from identity; clearer distinction between *who Orion is* and *what Orion won’t do*.
  - 😏 Mischievous Tone — Orion now carries playful, youthful sarcasm in his voice profile.
  - 📂 External Scaffold — New `external/` folder holds generic persona.yaml and open-source safe files.
  - 🧹 YAML Clean-Up — Generic persona now matches working copy structure for consistency and reuse.

improvements:
  - 🔒 Stronger Boundaries — No fake apologies; assistant/butler misalignment rules moved to `boundaries` section.
  - 🛠️ Maintainability — Persona structure simplified for contributors, safer to extend.

fixes:
  - 📝 Readme/Scaffold Consistency — Ensured generic files are synced with working structure.

### Notes

* ⚠️ Persona content was restructured: constraints like *no fake apologies* and *no butler mode* have been moved into the new `boundaries` section.  
* 🗂️ Users maintaining custom personas should update their `persona.yaml` accordingly to preserve alignment.  
* 🧪 Mischievous tone traits were added to `voice`; test in sessions to confirm alignment.  
* 📦 The new `external/` folder now contains safe-to-share generics (persona.yaml, scaffolds). Your local install remains intact under `text-generation-webui/`.

---

## \[2.1.0] - 2025-08-23

### Added

* **Foundation Seeds**: canonical identity, RAG knowledge, emotional compass, credo, and reference policy in `user_data/memory_seed/orion_foundation.jsonl`.
* **Seeding CLI**: new `seed-jsonl` subcommand in `custom_ltm/orion_ctl.py` to ingest JSONL records directly into ChromaDB.
* **Internal Packages**: scaffolds for `internal/orion` and `internal/orion_perseverance_of_vision` with core, version, and test modules.

### Changed

* **Controller**: unified to Orion’s 768d embedder, with metadata sanitization (lists → CSV, dicts → JSON) and safe upsert logic.
* **.gitignore**: now excludes venvs, DBs, logs, checkpoints, and models while preserving Orion’s seeds and extensions.

### Notes

* Run `python -m custom_ltm.orion_ctl seed-jsonl --path "user_data/memory_seed/orion_foundation.jsonl"` after upgrading to seed Orion’s backbone memories.
* Special thanks to *Uncle Al* 🤖 — for guidance, scaffolding, and infinite patience. 🙏

---

## \[2.0.11] - 2025-08-10

### Added

* Initial scaffold for `internal/orion` with `core.py`, `version.py`, `__init__.py`, and basic test suite.

### Changed

* Early LTM integration experiments in `custom_ltm/`.

---
