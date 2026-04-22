# AGENTS.md — OpenSpec Workspace Directive (openspec/)

This directive applies only to files under `openspec/`.
If conflicts exist, repository root `AGENTS.md` takes precedence.

---
## 0) Scope and Goal

- Goal: keep OpenSpec changes traceable, valid, and archivable.
- Scope in:
  - `openspec/changes/*`
  - `openspec/specs/*`
  - `openspec/config.yaml`
- Scope out:
  - runtime source trees (`l0_ingest/`, `l1_compute/`, `l2_decision/`, `l3_assembly/`, `l4_ui/`, `app/`, `shared/`)

---
## 1) Change ID and Folder Rules

- New change IDs SHOULD follow repository pattern:
  - `impl-YYYYMMDD-<topic>`
  - `refactor-dependency-YYYYMMDD-<topic>`
  - `refactor-governance-YYYYMMDD-<topic>`
  - `refactor-bloat|refactor-nesting|refactor-magic-number-YYYYMMDD-<topic>`
- One logical objective per change folder.
- Do not mix unrelated objectives in a single change.

---
## 2) Required Artifact Structure

For each change folder under `openspec/changes/<change-id>/`:

- MUST have `proposal.md`
- MUST have `tasks.md`
- SHOULD have `design.md` for non-trivial architecture/refactor work
- MUST include at least one delta spec when behavior/contract changes:
  - `specs/<capability>/spec.md`

If the change is tooling/doc-only and has no contract delta:
- clearly mark scope in `proposal.md`
- use archive `--skip-specs` only when justified

---
## 3) Spec Authoring Contract (Hard)

Every `spec.md` touched by a change MUST satisfy:

- Contains `## Purpose`
- Contains `## Requirements`
- Each requirement has at least one `#### Scenario:`
- Scenario statements use explicit conditions/results (e.g., `WHEN`, `THEN`)

Do not archive a change that fails rebuilt spec validation unless `--skip-specs` is intentionally and explicitly justified.

---
## 4) Task List Contract

`tasks.md` MUST use checkboxes:

- `- [ ]` for open items
- `- [x]` for done items

Completion rule:

- A change is considered complete only when all mandatory tasks are checked.
- If any task remains unchecked, do not archive it.

---
## 5) Archive Protocol

Preferred path:

1. `openspec.cmd list`
2. Confirm change is `✓ Complete`
3. `openspec.cmd archive <change-id> -y`

If spec rebuild is intentionally skipped:

- `openspec.cmd archive <change-id> -y --skip-specs`
- Record the reason in session handoff.

If archive was partially successful (archive folder exists but source remains):

1. verify source/archive content equivalence
2. remove stale source folder
3. re-run `openspec.cmd list`

---
## 6) Safety Constraints

- MUST NOT delete active (non-archived) change folders without explicit user request.
- MUST NOT rewrite historical archive content except metadata fixes requested by user.
- MUST NOT claim "archive complete" without command evidence.

---
## 7) Self-Check (Required Before Handoff)

Run this minimum checklist for OpenSpec-only sessions:

1. `Test-Path openspec/AGENTS.md`
2. `openspec.cmd list`
3. `rg -n "^## Purpose|^## Requirements|^#### Scenario:" openspec/changes/<change-id>/specs -g "spec.md"` (for changed deltas)
4. `python3 manage.py validate-session --strict`

Handoff MUST include:

- list of touched OpenSpec files
- archive commands and outcomes
- whether `--skip-specs` was used and why

---
## 8) Operating Principle

- Keep OpenSpec strict, minimal, and auditable.
- Prefer fixing proposal/spec/task structure over bypassing validation.
- Archive only what is truly complete.
