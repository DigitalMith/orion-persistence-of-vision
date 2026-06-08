# Orion Agent Tool Admission Checklist (v0)

This checklist governs which tools may be allowlisted in
`user_data/orion/data/agent_tools.yaml`.

It exists to preserve **safety, auditability, and clarity** as Orion evolves.

Agent Mode is an execution layer, not a reasoning system.
These rules are intentionally conservative.

---

## 0) Identity & Intent

- Tool name is **explicit and unambiguous** (describes what it does).
- Tool has **a single, well-defined purpose**.
- Tool outputs are **human-reviewable** (text, JSON, Markdown).
- Tool does not rely on hidden side effects.

---

## 1) Safety Tier (Required)

Every tool must declare a safety tier:

- **Tier 0 — Read-only**
  - Inspection, queries, status, reporting.
  - No writes of any kind.

- **Tier 1 — Dry-run / Plan-only**
  - Generates plans, previews, diffs, or reports.
  - No mutations to persona, memory, DB, or filesystem.

- **Tier 2 — Reversible Write**
  - Writes are idempotent, append-only, or easily rolled back.
  - Requires explicit confirmation.

- **Tier 3 — Destructive**
  - Deletes, overwrites, resets, or irreversible actions.
  - Strongly discouraged.
  - Must have a Tier 1 dry-run sibling.
  - Requires stronger confirmation and special review.

Default policy: **only Tier 0 and Tier 1 tools are allowed early**.

---

## 2) Inputs & Argument Discipline

- `allow_args` defaults to false.
- If `allow_args: true`, arguments must be:
  - bounded (enum, whitelist, or range-limited)
  - non-shell (no free-form command strings)
  - non-arbitrary-path (paths must be sandboxed or centrally resolved)
- Tool must remain safe under all valid argument combinations.

---

## 3) Confirmation & Escalation

- Tier 2 and Tier 3 tools require a `confirm` token.
- Confirmation must guard the **actual mutation**, not just enqueue.
- Tier 3 requires a stronger, distinct confirmation token.
- No silent escalation paths.

---

## 4) Composition Rules (Non-Negotiable)

- Tool must not enqueue other tools.
- Tool must not invoke `tick`.
- Tool must not mutate agent state directly.
- Tool must not start background loops, daemons, or watchers.

Agent Mode executes exactly one explicit action at a time.

---

## 5) Determinism & Auditability

- Same inputs should produce the same outputs.
- Any nondeterminism must be explicit and logged.
- Tool must emit:
  - a clear summary of what happened
  - optional artifact output (plan, report, diff) in a known location
- Failures must be loud and obvious.

---

## 6) Path & Environment Hygiene

- No current-working-directory assumptions.
- All paths resolved through centralized path logic.
- No implicit environment mutation.
- No network access unless explicitly intended and separately reviewed.

---

## 7) Data Boundary Declaration (Orion-Specific)

Each tool must declare which boundary it touches:

- identity
- persona
- episodic memory
- semantic memory
- ChromaDB
- filesystem

Any tool capable of mutating **persona** or **semantic promotion**
is treated as destructive by policy, regardless of scope.

---

## 8) “Exists as Safe First” Rule

- A tool must be useful as Tier 0 or Tier 1 first.
- Graduation to write-capable tiers requires:
  - real usage
  - confidence
  - explicit decision
- No skipping straight to mutation.

---

## 9) 30-Second Allowlist Rubric

A tool may be allowlisted only if all are true:

- It is Tier 0 or Tier 1.
- It works with `allow_args: false`.
- It does not mutate persona, memory, or DB.
- It does not accept arbitrary paths or shell strings.
- It produces a human-reviewable result.

Any “no” means the tool stays out or must be redesigned.

---

This checklist is authoritative.
When in doubt: prefer fewer tools, smaller tools, and clearer tools.
