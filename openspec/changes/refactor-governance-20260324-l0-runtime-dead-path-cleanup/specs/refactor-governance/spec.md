## ADDED Requirements

### Requirement: L0 V2 Runtime Tree Must Not Retain Orphan Side Paths
Files under `l0_ingest/v2/source/runtime/` SHALL belong to the active runtime path selected by the L0 facade/factory or to direct helpers used by that path.

#### Scenario: Orphan runtime adapter remains in the active tree
- **WHEN** a runtime adapter under `l0_ingest/v2/source/runtime/` is not imported by the active factory/export path
- **THEN** it MUST be removed from the active runtime tree
- **AND** it MUST NOT preserve legacy imports that bypass current `v2` boundaries.

### Requirement: L0 Event Processing Must Have One Active Runtime Processor
The active L0 normalize event path SHALL expose exactly one runtime event processor for facade consumption.

#### Scenario: Duplicate processor survives after hard cut
- **WHEN** a legacy event processor under `l0_ingest/v2/normalize/events/` is no longer exported or consumed by the facade
- **THEN** it MUST be removed or archived outside the active runtime tree
- **AND** the live runtime path SHALL continue through the single exported processor.
