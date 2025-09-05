# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

<!--CHANGELOG_START-->

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
