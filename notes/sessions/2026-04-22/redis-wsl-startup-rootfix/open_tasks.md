# Open Tasks

## Priority Queue
- [x] P0: move Redis persistence ownership off `/mnt/e` and onto WSL ext4. (2026-04-22 10:16 ET)
  - Owner: Codex
  - Definition of Done: Redis config and startup owner resolve to `./var/redis` on `ext4`, with no remaining `/mnt/*` runtime path in the standard startup contract.
  - Blocking: none
- [x] P0: add strict Redis preflight to `start-all`. (2026-04-22 10:06 ET)
  - Owner: Codex
  - Definition of Done: `/mnt/*`, non-`ext4`, and multipart AOF totals above `2 GiB` fail before backend/frontend startup.
  - Blocking: none
- [x] P1: compact the existing Redis dataset after ext4 cutover. (2026-04-22 10:17 ET)
  - Owner: Codex
  - Definition of Done: the migrated ext4 Redis owner completes `BGREWRITEAOF`, and the resulting base/incr total falls well below the strict cap.
  - Blocking: none
- [x] P1: re-verify full-stack startup and Windows browser path after Redis cutover. (2026-04-22 10:19 ET)
  - Owner: Codex
  - Definition of Done: host `start-all` is green and Windows `localhost:5173` plus same-origin `/api` respond successfully.
  - Blocking: none

## Parking Lot
- [ ] Consider whether a repo-owned diagnostic should surface the host `vm.overcommit_memory` warning more explicitly.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added Redis preflight regression coverage for `/mnt/*`, non-`ext4`, oversized AOF totals, and valid ext4 acceptance. (2026-04-22 10:07 ET)
- [x] Host migration rewrote the old `3.47GiB` multipart AOF down to a compact ext4 base/incr set and reduced Redis cold-start load from `441.844s` to `0.129s` after compaction. (2026-04-22 10:19 ET)
