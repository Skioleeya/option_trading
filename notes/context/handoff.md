# Handoff (Index)

## Active Handoff
- Path: notes/sessions/2026-03-25/trace-depth-profile-and-tradingview-live-path-20260325/handoff.md
- Meta: notes/sessions/2026-03-25/trace-depth-profile-and-tradingview-live-path-20260325/meta.yaml

## Latest Outcome
- Session: 2026-03-25/trace-depth-profile-and-tradingview-live-path-20260325
- Summary: `DepthProfile` is confirmed live through the websocket payload; TradingView live `atm` is null after hours because the ATM tracker suppresses output outside regular hours. Added `[L3-PAYLOAD]` and `[L4 ATM]` debug markers so operators can see that distinction directly, and `scripts/validate_session.ps1 -Strict` passed.

## Next Session Bootstrap
1. Read this file.
2. Read notes/context/project_state.md and notes/context/open_tasks.md.
3. Open the active session folder and continue from its handoff.md.
