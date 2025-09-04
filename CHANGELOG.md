# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
