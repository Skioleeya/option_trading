## Context

The current runtime has two parallel ingestion surfaces:

- Rust SHM polling path (high-frequency quote/depth/trade payloads)
- Event-queue processor path with depth/trade callback fan-out

Feature collapse appears when SHM-origin events update quote/store state but do not consistently drive L1 microstructure state updates.

At the same time, L2 feature extractors mix dict-based and typed/columnar assumptions, creating compatibility gaps for `RecordBatch` snapshots.

## Decisions

1. **Event bridge completeness**
   - In `OptionChainBuilder._rust_consumer_loop`, route SHM depth/trade semantics into the same L1 microstructure callback path used by event-queue mode.
   - Do not bypass callback hooks for SHM events that carry microstructure signal value.
   - Keep ingestion ownership in L0; L1 only consumes callback-level normalized events.

2. **Impact extraction compatibility**
   - `peak_impact` extraction supports both:
     - list/dict chain rows (legacy path)
     - Arrow `RecordBatch` chain rows (runtime fast path)
   - Gamma source compatibility:
     - prefer computed/runtime gamma column when present
     - preserve legacy fallback for historical dict payloads

3. **Turnover fallback policy**
   - Source priority:
     1. WS turnover (authoritative when present)
     2. REST turnover fallback (only when WS turnover unavailable)
     3. REST current_volume fallback (bounded fallback for velocity continuity)
   - Fallback behavior is explicit and auditable.
   - Field meaning and availability are aligned with:
     - `docs/LONGPORT_OPTION_FIELD_DICTIONARY.md`
     - `docs/LONGPORT_LLMS_EFFECTIVE_FIELDS.md` (navigation/official endpoint context)

## Failure Handling and Degrade Rules

- Any bridge failure must emit explicit structured logs with source/event type.
- Bridge failure must not block L4 broadcast continuity.
- If high-fidelity signal input is unavailable, system may degrade feature values but must preserve observability and no-silent-failure semantics.

## Architecture Boundaries

- No reverse dependency introduction.
- No `l2_decision -> l3_assembly/l4_ui` coupling.
- Reusable cross-layer logic stays in neutral contract/service boundaries when needed.

