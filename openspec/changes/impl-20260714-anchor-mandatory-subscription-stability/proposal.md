# Anchor Mandatory Subscription Stability

## Summary
Make ATM decay anchor legs a compute-loop protected mandatory subscription set so dynamic subscription rebalance cannot drop the current anchor when housekeeping is halted by strict ActiveOptions failures.

## Scope
- App orchestration for ATM decay anchor mandatory sync.
- L0 subscription refresh/repair trigger through existing public `OptionChainBuilder` APIs.
- Subscription stability tests, L0/L1 SOP updates, and session evidence.

## Non-Goals
- No L4 color semantic changes; `CALL=red` and `PUT=green` remain fixed.
- No L1 numerical compute changes.
- No change to ActiveOptions strict hard-fail semantics.
