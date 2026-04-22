# Open Tasks

## Priority Queue
- [x] P0: Point `origin` to `git@github.com:Skioleeya/option_trading.git`.
  - Owner: Codex
  - Definition of Done: `git remote -v` shows the provided SSH URL for fetch/push.
  - Blocking: None.
- [x] P1: Probe the new remote from the Windows host.
  - Owner: Codex
  - Definition of Done: `git ls-remote --heads origin` attempted after the SSH link change and recorded the result.
  - Blocking: None.
- [x] P2: Sync session/context records and close the session.
  - Owner: Codex
  - Definition of Done: session files updated; strict validation passes.
  - Blocking: None.

## Parking Lot
- If the user later wants a named per-repo SSH identity instead of the default `id_ed25519`, add an explicit `%USERPROFILE%\\.ssh\\config` entry in a separate host-credential session.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Switched local `origin` from HTTPS to the provided GitHub SSH URL. (2026-04-22 17:09 ET)
- [x] Generated a new local `ed25519` key, added its public key to GitHub, and removed the accidental local passphrase so OpenSSH can use it non-interactively. (2026-04-22 17:18 ET)
- [x] Verified GitHub SSH auth with `ssh -T git@github.com` and confirmed `git ls-remote --heads origin` returns remote refs. (2026-04-22 17:19 ET)
