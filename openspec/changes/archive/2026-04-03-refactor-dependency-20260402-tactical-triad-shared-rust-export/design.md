## Context

`shared/services/active_options_engines.py` and `shared/services/active_options_input.py`
are pure re-export shims. Their runtime logic already lives in `shared_rust.services`, so
the remaining work is to retire the shims and retarget consumers directly to the neutral
Rust-backed surface.

## Goals / Non-Goals

**Goals:**
- remove the two pure-shim files
- retarget the four L2 flow consumers and `app/loops/compute_loop.py` to `shared_rust.services`
- keep runtime behavior unchanged while collapsing the indirection layer

**Non-Goals:**
- no Rust owner implementation changes
- no behavior changes in `shared_rust.services`
- no edits to `shared/services/active_options_runtime.py` or `shared/services/active_options_constants.py`

## Decisions

1. Prefer direct imports from `shared_rust.services` instead of adding another wrapper.
   - Rationale: the shim layer adds no logic and only increases migration surface.
2. Move the two `ACTIVE_OPTIONS_INPUT_REASON_*` string constants inline if they are still
   referenced by `compute_loop.py`.
   - Rationale: the constants are only needed at the call site and do not justify a standalone shim.
3. Delete the shim files in the same change set as consumer retargeting.
   - Rationale: avoids a transitional state where both the shim and the direct surface remain live.

## Risks / Trade-offs

- [Risk] a residual runtime import remains after deletion -> [Mitigation] run the runtime-source grep scan listed in tasks.
- [Risk] direct import surface changes smoke out a latent export mismatch -> [Mitigation] run consumer import smoke tests and strict validation.

## Migration Plan

1. Retarget consumer imports.
2. Delete the two shim files.
3. Run residual reference scan and smoke tests.
4. Close the change only after strict session validation passes.
