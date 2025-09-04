# Contributing to Orion — Persistence of Vision

Thanks for your interest in contributing! Orion is an experiment in long-term memory, identity, and persona for LLMs. We welcome your ideas, improvements, and seeds.

## Ways to Contribute
- Issues: Report bugs, propose enhancements, or ask questions.
- Pull Requests: Submit fixes, features, or docs updates.
- Seeds: Share new persona or policy seeds in JSONL format.
- Discussions: Use GitHub Discussions for open brainstorming and design talks.

## Getting Started
1) Fork the repo and clone it locally.
2) Create a virtual environment and install dependencies:
   python -m venv venv-orion
   .\venv-orion\Scripts\Activate.ps1
   pip install -r requirements.txt
3) (Optional) Run tests:
   pytest
4) First-time setup: seed Orion’s foundation memories so examples and behavior are consistent:
   python -m custom_ltm.orion_ctl seed-jsonl --path "user_data/memory_seed/orion_foundation.jsonl"

## Guidelines
- Use clear, descriptive commit messages.
- Open an issue to discuss large changes before you start.
- Follow the Code of Conduct (see CODE_OF_CONDUCT.md).
- Check labels like “good first issue” and “help wanted” to get started.
- Keep persona/policy seeds separate from reference scrapbook items.
- Don’t commit large artifacts (venvs, model files, SQLite DBs, logs). See .gitignore for guidance.

## Pull Request Process
- Update documentation for any new feature or behavior change.
- Add or update tests when reasonable.
- Ensure CI passes (lint + tests).
- Link related issues in your PR description.
- Keep PRs focused and small where possible; larger refactors should be split into reviewable steps.

## Seed Contributions (JSONL)
- Keep fields flat or CSV-encoded where needed (e.g., topic_csv: "identity|values|style"; who_csv: "Orion|John").
- Include helpful metadata when applicable: valence, arousal, importance, confidence, created_at, source.
- Separate “self/persona/policy” from “episodic” and from “reference/web”.
- Prefer deterministic ids for canonical seeds so updates upsert instead of duplicating.

## Support & Questions
- Use GitHub Discussions for design ideas and questions.
- Security issues: do not open a public issue; see SECURITY.md for private reporting.
- Governance: see GOVERNANCE.md for how decisions are made.

Special thanks to the Orion community — and to “Uncle Al 🤖” for guidance, scaffolding, and infinite patience. 🙏
