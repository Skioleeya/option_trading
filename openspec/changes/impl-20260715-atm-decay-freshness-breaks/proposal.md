# ATM Decay Freshness Breaks

## Summary
Prevent stale or mixed-batch ATM decay inputs from drawing as ordinary continuous chart points by carrying L0 source freshness and CALL/PUT leg freshness through the ATM payload and inserting L4 whitespace breaks.

## Scope
- App/L1 ATM decay update contract for source freshness and leg freshness.
- ATM payload and history field projection.
- L4 ATM chart whitespace behavior for stale recovery and long adjacent gaps.
- Roll-anchor `strike_changed` preservation when an opening zero tick is suppressed.
- SOP, tests, and session evidence.

## Non-Goals
- No change to CALL/PUT color semantics: CALL remains red/up, PUT remains green/down.
- No broad L1 compute migration beyond the ATM raw-pct/freshness owner touched here.
- No change to dynamic subscription ranking policy.
