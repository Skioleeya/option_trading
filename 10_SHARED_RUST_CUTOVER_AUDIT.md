# Shared Rust Cutover Audit

## Current State
- Audit time (ET): 2026-04-01 14:15:00 -04:00
- `shared/` remaining Python files after Wave 0/Wave 1 leaf delete sweep: `125`
- `shared/tests` Python files: removed

## Remaining Python Distribution
- `shared/services`: `96`
- `shared/config`: `11`
- `shared/config_cloud_ref`: `0`
- `shared/system`: `8`
- `shared/models`: `4`
- `shared/contracts`: `4`
- `shared/cache`: `1`

## Objective Assessment
This repository state does not support a truthful claim that `shared/` has been fully converted to Rust in this slice.

Reasons:
- the remaining Python surface is large and spans runtime, config, contracts, models, and system helpers
- many modules are active runtime owners, not dead wrappers
- deleting the remaining `137` Python files without one-by-one Rust owner replacement would break L0-L4 contracts

## Completed In This Slice
- deleted `shared/tests/test_metric_semantics.py`
- deleted `shared/tests/test_realized_volatility.py`
- removed the `shared/tests` directory because only cache artifacts remained
- deleted 9 zero-hit dead leaves under `shared/config_cloud_ref/*`
- deleted `shared/config_cloud_ref/agent_g.py` after moving the last active governance reference to `shared/config/agent_g.py`
- deleted `shared/config_cloud_ref/__init__.py` because the cloud-ref package no longer had any live runtime, test, SOP, or active OpenSpec consumers
- deleted `shared/models/active_option.py` because it was no longer referenced by runtime, package exports, dynamic loaders, or active tests

## Wave 0 Result

- all other `config_cloud_ref` leaf modules were removed as dead references

## Required Next Waves
1. `shared/services/*` Rust cutover by bounded owner groups
2. `shared/config*` replacement or retirement plan
3. `shared/system/*` transport/helper migration
4. `shared/contracts/*` Rust single-source contract generation
5. `shared/models/*` Rust-native model ownership

## Constraint
A full `shared/` Rust cutover must be executed as multiple validated migration waves. A single-shot delete of the remaining Python surface is not engineering-safe.
