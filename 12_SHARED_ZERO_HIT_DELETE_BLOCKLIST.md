# Shared Zero-Hit Delete Blocklist

## Retained In Wave 0

These Python files were examined during Wave 0 and explicitly retained.

### `shared/services/active_options/test_*.py`
- retained because they are still referenced by active and historical verification flows
- they are not zero-hit dead tests

### All remaining `shared/services/*`, `shared/system/*`, `shared/contracts/*`, `shared/models/*`, `shared/config/*`
- retained because they are active owners or require owner-by-owner Rust replacement rather than Wave 0 deletion
