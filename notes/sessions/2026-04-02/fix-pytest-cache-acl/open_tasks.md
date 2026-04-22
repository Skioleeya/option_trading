# Open Tasks

## Priority Queue
- [x] P0: restore host-side write access for `tmp/pytest_cache`
  - Owner: Codex
  - Definition of Done: host-level writes to the cache root succeed again
  - Blocking: unrestricted host context was needed to apply and verify the ACL repair
- [x] P1: restore child directory creation under `tmp/pytest_cache/research_store_tests`
  - Owner: Codex
  - Definition of Done: the historical research-store cache subtree can create children again in host context
  - Blocking: unrestricted host context was needed for verification
- [x] P2: harden the pytest entrypoint around cache ACL failures
  - Owner: Codex
  - Definition of Done: `scripts/test/run_pytest.ps1` fails fast with a targeted message and a dedicated repair script exists
  - Blocking: none

## Parking Lot
- [ ] If the broader `tmp/` tree needs the same normalization later, keep that as a separate session from pytest-cache-only remediation.
- [ ] If another account starts recreating sandbox-owned cache trees, document the repair script in local onboarding notes.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Restored host-side `tmp/pytest_cache` writes and added a deterministic repair path (2026-04-02 08:32 ET)
