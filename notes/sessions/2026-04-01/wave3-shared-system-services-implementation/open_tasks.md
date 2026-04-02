# Open Tasks

## Priority Queue
- [x] P0: cut over Wave 3 IPC transport cluster (`shared/system/ipc_*`) plus direct consumers.
  - Owner: Codex
  - Definition of Done: Rust native owner in place, stable reader/signal imports preserved, targeted IPC regressions green, SOP/OpenSpec/session updated.
  - Blocking: none
- [x] P0: cut over `shared/system/tactical_triad_logic.py` plus mapped L2/L3/shared consumers.
  - Owner: Codex
  - Definition of Done: Rust-backed tactical-triad owner in place, consumer API preserved, mapped regressions green, SOP/OpenSpec/session updated.
  - Blocking: none
- [x] P1: cut over the bounded `shared/services/*` helper/schema cluster (`history_columnar`, `header_volatility_context`, `research_feature_store_schema`).
  - Owner: Codex
  - Definition of Done: Rust native helper/schema owner in place, stable consumer APIs preserved, mapped `app`/`l3_assembly` regressions green, SOP/OpenSpec/session updated.
  - Blocking: none
- [x] P1: cut over the bounded `shared/services/*` research-store query-shaping cluster (`research_feature_store_io` compact/projection/interval semantics).
  - Owner: Codex
  - Definition of Done: Rust native query-shaping owner in place, stable `ResearchFeatureStore` and `/history` APIs preserved, mapped `app`/`l3_assembly` regressions green, SOP/OpenSpec/session updated.
  - Blocking: none
- [x] P1: cut over the bounded `shared/services/*` research-store export/retention helper cluster (`research_feature_store_io` JSONL export and cleanup candidate semantics).
  - Owner: Codex
  - Definition of Done: Rust native export/retention helper owner in place, stable `ResearchFeatureStore` and `/history` APIs preserved, mapped regressions green, SOP/OpenSpec/session updated.
  - Blocking: none
- [x] P1: cut over the bounded `shared/services/*` research-store append/label helper cluster (`research_feature_store` emit-decision, longport normalization, label serialization semantics).
  - Owner: Codex
  - Definition of Done: Rust native append/label helper owner in place, stable `ResearchFeatureStore` API preserved, mapped regressions green, SOP/OpenSpec/session updated.
  - Blocking: none
- [x] P1: cut over the bounded `shared/services/*` research-store file-selection helper cluster (`research_feature_store_io` range-file and latest-file selection semantics).
  - Owner: Codex
  - Definition of Done: Rust native file-selection helper owner in place, stable `ResearchFeatureStore` and `/history` APIs preserved, mapped regressions green, SOP/OpenSpec/session updated.
  - Blocking: none
- [x] P1: cut over the bounded `shared/services/*` research-store storage execution cluster (`research_feature_store*` parquet/storage helpers).
  - Owner: Codex
  - Definition of Done: Rust native storage execution owner in place, stable `ResearchFeatureStore` and `/history` APIs preserved, mapped regressions green, SOP/OpenSpec/session updated.
  - Blocking: none
- [ ] P1: cut over the next non-research-store `shared/services/*` runtime-owner cluster.
  - Owner: Codex
  - Definition of Done: bounded runtime/I-O service owner group migrated or retired with all mapped consumers and tests.
  - Blocking: requires selecting the next bounded cluster after Wave 3 research-store completion.

## Parking Lot
- [ ] Decide whether system/service native exports should eventually split from the L0 extension into a dedicated package.
- [ ] Revisit whether thin Python wrappers can disappear after broader cross-repo consumer convergence.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Wave 3 tactical-triad cluster completed (2026-04-01 16:52:00 -04:00)
- [x] Wave 3 bounded services helper/schema cluster completed (2026-04-01 17:28:00 -04:00)
- [x] Wave 3 research-store query-shaping cluster completed (2026-04-01 17:45:00 -04:00)
- [x] Wave 3 research-store export/retention helper cluster completed (2026-04-01 18:02:00 -04:00)
- [x] Wave 3 research-store append/label helper cluster completed (2026-04-01 18:18:00 -04:00)
- [x] Wave 3 research-store file-selection helper cluster completed (2026-04-01 18:29:00 -04:00)
- [x] Wave 3 research-store storage execution cluster completed (2026-04-01 18:44:00 -04:00)
