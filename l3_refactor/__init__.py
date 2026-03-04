"""l3_refactor — L3 Output Assembly Layer (Strangler Fig refactor).

Architecture:
    DecisionOutput (L2) + EnrichedSnapshot (L1) + AtmDecay
        │
        ▼
    PayloadAssemblerV2 (COW, strong-typed)
        │
        ▼
    FrozenPayload (immutable contract)
        │
        ├─→ FieldDeltaEncoder → DeltaPayload
        ├─→ TimeSeriesStoreV2 (Hot/Warm/Cold)
        └─→ BroadcastGovernor (1Hz, JSON legacy / future binary)
"""

__version__ = "3.1.0-l3-refactor"
