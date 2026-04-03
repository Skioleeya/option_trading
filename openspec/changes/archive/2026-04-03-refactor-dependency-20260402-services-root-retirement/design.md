## Context

`shared_rust/services_root.pyd` was a transitional namespace artifact from earlier migration waves.
`shared_rust.services` is now the neutral, active service namespace and already exports a superset
of symbols previously reachable through `services_root`.

## Goals

- retire `services_root.pyd` to reduce migration surface area
- keep all consumers on `shared_rust.services`
- avoid introducing any new wrapper or compatibility layer

## Non-Goals

- no Rust source implementation changes
- no Python runtime behavior changes
- no new `.pyd` artifacts

## Controls

1. Deletion-only scope: remove `shared_rust/services_root.pyd`.
2. Import continuity: verify `shared_rust.services` imports still pass.
3. Negative import assertion: verify `shared_rust.services_root` import fails.
4. No shim backfill: do not add replacement Python shim.

## Risk

Low. No runtime consumer import sites remain under runtime source trees.
