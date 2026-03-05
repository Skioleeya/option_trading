## 1. L0 Infrastructure & Schema

- [ ] 1.1 Add `impact_index: float` to `FlowEngineOutput` in `shared/models/flow_engine.py`
- [ ] 1.2 Initialize default value of 0.0 to ensure backward compatibility

## 2. L2 Feature Collection (Turnover)

- [ ] 2.1 Implement `TurnoverVelocityExtractor` in `l2_decision/feature_store/extractors.py`
- [ ] 2.2 Register new extractor in `build_default_extractors` for the 1Hz compute loop

## 3. L2 Spatial Clustering (Sweep Logic)

- [ ] 3.1 Develop `InstitutionalSweepDetector` inside `l2_decision/signals/flow/deg_composer.py`
- [ ] 3.2 Implement strike proximity window searching ($\pm 2$ strikes) for Z-Score reinforcement

## 4. L2 OFII Algorithm (Core Math)

- [ ] 4.1 Implement the $OFII$ formula in `l2_decision/signals/flow/flow_engine_g.py`
- [ ] 4.2 Integrate time-to-close ($\tau$) exponential decay factor into the calculation

## 5. L2 Signal Fusion Alignment

- [ ] 5.1 Update `FlowEngineG` to output the calculated `impact_index` in its result object
- [ ] 5.2 Implement the $1.25x$ signal boost for sweep-detected strikes

## 6. L3 Assembly & Calculation

- [ ] 6.1 Refactor `ActiveOptionsPresenter` in `l3_assembly/presenters/ui/active_options/presenter.py` to handle OFII data
- [ ] 6.2 Implement cross-strike sorting logic using the new index

## 7. L3 UI Payload Injection

- [ ] 7.1 Include `impact_index` in the final serialized payload sent to the frontend
- [ ] 7.2 Ensure proper precision rounding for UI performance

## 8. L2 Unit Testing (Logic)

- [ ] 8.1 Create `tests/l2_decision/test_clustering_logic.py` to verify institutional sweep detection
- [ ] 8.2 Create `tests/l2_decision/test_impact_math.py` to validate OFII calculations across different session times

## 9. L3 Integration Testing (Sorting)

- [ ] 9.1 Create `tests/l3_assembly/test_active_options_sorting.py` to verify ranking behavior
- [ ] 9.2 Validate that high-gamma threats outrank high-volume noise in test scenarios

## 10. Shadow Mode & Audit Alignment

- [ ] 10.1 Update `DecisionAuditEntry` to include the new `impact_index` telemetry
- [ ] 10.2 Verify that the JSONL audit logs correctly capture the updated signal DNAs

## 11. Frontend Type Alignment (L4)

- [ ] 11.1 Update TypeScript interface for `ActiveOption` in `l4_ui/src/types/dashboard.ts` to include `impact_index`

## 12. UI Dashboard Refresh (L4)

- [ ] 12.1 Update `ActiveOptions` table to display the "Impact" score alongside Volume
- [ ] 12.2 Apply visual highlighting (e.g., subtle glow) for strikes classified as "Institutional Sweaps"

## 13. System Verification & Documentation

- [ ] 13.1 Run end-to-end simulation to verify sub-50ms compute latency
- [ ] 13.2 Update `README.md` with descriptions of the new institutional-grade metrics
