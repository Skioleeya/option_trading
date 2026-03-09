## 1. Cutover

- [ ] 1.1 Remove `primary_ctx` bootstrap from app startup path.
- [ ] 1.2 Finalize runtime default as `rust_only`.
- [ ] 1.3 Ensure no runtime private-member cross-layer access introduced.

## 2. Docs and Process

- [ ] 2.1 Update SOP files to reflect rust-only flow.
- [ ] 2.2 Update session handoff with strict validation evidence.

## 3. Verification

- [ ] 3.1 Run focused L0 tests and pipeline regression entry.
- [ ] 3.2 Run `scripts/validate_session.ps1 -Strict` and keep output in handoff.

