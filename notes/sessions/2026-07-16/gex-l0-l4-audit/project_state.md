# Project State

## Snapshot
- DateTime (ET): 2026-07-16 09:48 -04:00
- Branch: codex/research-persistence-startup-fixes-20260423
- Last Commit: d89a877
- Environment:
  - Market: OPEN
  - Data Feed: OK by backend /health and live WS payload availability
  - L0-L4 Pipeline: OK for GEX payload path; UI browser reconciliation not run because Playwright is missing from .venv

## Current Focus
- Primary Goal: Audit GEX L0-L4 business logic and determine whether current calculation is correct.
- Scope In: GEX formula, unit scale, call/put sign convention, wall/flip semantics, L2 normalization, L3 payload mapping, L4 display consumption, targeted tests.
- Scope Out: Runtime code changes, dependency installation, start-all restart, true dealer-inventory model redesign.

## Findings
- L0 does not own GEX calculation. It supplies chain rows, spot, IV, OI, multiplier, timestamps, and diagnostics. This matches SOP: L0 must not compute legacy Greeks/GEX.
- L1 current formula matches SOP: `gamma * open_interest * contract_multiplier * spot^2 * 0.01 / 1_000_000`, producing Million USD for a 1% spot move.
- L1 call and put gross GEX are non-negative magnitude buckets; `net_gex = total_call_gex - total_put_gex`.
- L1 cumulative flip and zero-gamma are correctly separated: `flip_level_cumulative` is strike-sorted cumulative net GEX crossing, while `zero_gamma_level` recomputes net GEX over a spot grid and returns the zero crossing nearest spot.
- L2 uses `net_gex / 1000` for `$1B` normalization and uses `spot < zero_gamma_level` for gamma_flip when zero-gamma is available.
- L3 maps `agent_g.data.net_gex`, `gamma_walls`, and `gamma_flip_level` from L1/L2 snapshot data, with `gamma_flip_level` bound to valid positive `zero_gamma_level`.
- L4 displays `agent_g.data.net_gex` through `fmtGex`, where values are interpreted as Million USD and rendered as `M` or `B`.

## Verification
- Live backend health: `curl.exe -fsS http://127.0.0.1:8001/health` returned status ok.
- Frontend health: `curl.exe -fsS http://127.0.0.1:5173` returned the app HTML.
- Live WS GEX sample: `agent_g.data.net_gex=-257.9`, `gamma_walls.call_wall=755.0`, `gamma_walls.put_wall=750.0`, `gamma_flip_level=752.53`.
- Backend targeted tests: 17 passed via `python manage.py run-pytest`.
- L4 targeted tests: 10 passed via `npm --prefix l4_ui run test -- gexStatus rightPanelModel decisionEngine.render`.
- Strict validation: `python manage.py validate-session --strict` passed.

## Risks / Constraints
- Contract risk: `PayloadAssembler._build_ui_state()` catches `MicroStatsPresenterV2.build()` exceptions and emits zero state. For unknown `gex_regime`, this conflicts with the L3 SOP fail-fast requirement and can mask contract drift.
- Wording risk: `l3_assembly/presenters/ui/micro_stats/mappings.py` comments still describe "做市商视角/净头寸", while current SOP says GEX is an OI-based structural proxy, not dealer inventory truth.
- Verification constraint: `scripts/diagnostics/reconcile_net_gex_online.py` could not run because `playwright` is not installed in the active .venv.

## Next Action
- Immediate Next Step: If requested, fix the L3 fail-fast masking and wording drift in a separate implementation session.
- Owner: Codex
