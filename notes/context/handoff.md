# Handoff (Index)

## Active Handoff
- Path: notes/sessions/2026-03-26/active-options-min-volume-ab-startup-fix-20260326/handoff.md
- Meta: notes/sessions/2026-03-26/active-options-min-volume-ab-startup-fix-20260326/meta.yaml

## Latest Outcome
- Session: 2026-03-26/active-options-min-volume-ab-startup-fix-20260326
- Summary: Fixed the restart-time `lifespan` crash that blocked the ActiveOptions min-volume A/B, recovered the backend via elevated strict restart, completed the bounded live `FLOW_ACTIVE_MIN_VOLUME` A/B, and added a debug-only aligned capture route/script. Same-version artifacts now exist from the live backend, but a 180-second watch still did not produce `sparse_window=true`, so the remaining proof item is waiting on thinner live conditions rather than missing tooling.

## Next Session Bootstrap
1. Read this file.
2. Read notes/context/project_state.md and notes/context/open_tasks.md.
3. Open the active session folder and continue from its handoff.md.
