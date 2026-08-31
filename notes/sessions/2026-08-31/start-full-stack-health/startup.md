# Startup: start-full-stack-health

STARTUP-PROOF: User requested a standard full-stack startup and liveness confirmation on 2026-08-31 ET.

## Session

- Session ID: `2026-08-31/start-full-stack-health`
- Scope: Start the existing runtime and capture liveness evidence.

## Scope Understanding

- In scope: `manage.py start-all`, Redis/backend/frontend readiness, health probes.
- Out of scope: Runtime code, configuration, broker credentials, and deployment changes.

## Prior Context Read

- `notes/context/project_state.md`
- `notes/context/open_tasks.md`
- `notes/context/handoff.md`
- `docs/SOP/SYSTEM_OVERVIEW.md`
- `docs/SOP/L0_DATA_FEED.md`
- `docs/SOP/L1_LOCAL_COMPUTATION.md`
- `docs/SOP/L2_DECISION_ANALYSIS.md`
- `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
- `docs/SOP/L4_FRONTEND.md`

## Recent Git Context

- Key commits reviewed: N/A: no code change requested.
- Initial state: Redis 6380 listening; backend 8001 and frontend 5173 unavailable.

## Worker Readiness

- Risks noticed: LongPort strict connectivity can fail startup by design.
- Blockers noticed: None before standard startup attempt.
