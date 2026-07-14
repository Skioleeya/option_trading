## Implementation
- [x] Add app-level anchor mandatory sync helper.
- [x] Call anchor sync from compute-loop ATM update paths.
- [x] Keep housekeeping anchor set as a lightweight fallback before ActiveOptions work.
- [x] Align local runtime subscription cap to the official 500 limit.

## Verification
- [x] Add anchor mandatory sync unit coverage.
- [x] Add compute-loop regression coverage for refresh/repair churn avoidance.
- [x] Run targeted pytest via `python manage.py run-pytest`.
- [x] Run `python manage.py validate-session --strict`.
- [x] Capture `python manage.py start-all` health evidence.
