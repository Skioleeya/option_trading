# Open Tasks

## Priority Queue
- No active session-local tasks. The startup doc semantic sync is complete.

## Parking Lot
- None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Rewrote `最新的启动步骤文档.md` so it matches the current `start-all` implementation and verified host behavior line-for-line in meaning. (2026-04-22 18:40 ET)
- [x] Re-verified the live host stack after the doc rewrite: `start-all --verify-only` all `True`, backend `/health` OK, frontend `200`. (2026-04-22 18:40 ET)
