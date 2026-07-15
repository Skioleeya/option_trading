## Implementation
- [x] Add ATM source freshness context at the app/L1 update boundary.
- [x] Extend ATM payload/history contracts with source freshness and leg freshness fields.
- [x] Enforce CALL/PUT same-freshness validation before raw pct output.
- [x] Preserve `strike_changed` across suppressed opening zero ticks.
- [x] Insert L4 chart whitespace for stale recovery and long adjacent gaps.
- [x] Update SOP and session evidence.

## Verification
- [x] Add/update backend unit coverage for stale source, leg freshness, and strike_changed preservation.
- [x] Add/update L4 chart/history coverage for stale recovery and gap whitespace.
- [x] Run targeted pytest via `python manage.py run-pytest`.
- [x] Run L4 tests/build as applicable.
- [x] Run `python manage.py validate-session --strict`.
