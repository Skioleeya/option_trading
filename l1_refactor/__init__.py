"""l1_refactor — L1 Local Computation Layer Refactoring Package.

> Strangler Fig pattern — coexists with backend/app/services/analysis/
> Validated modules replace existing ones incrementally.

Architecture:
    l1_refactor/
    ├── compute/        # GPUGreeksKernel + ComputeRouter
    ├── aggregation/    # StreamingAggregator (incremental GEX/Vanna)
    ├── iv/             # IVResolver + SABRCalibrator
    ├── microstructure/ # VPIN v2 + BBO v2 + VolAccel v2
    ├── time/           # TTM v2 (holiday calendar + settlement)
    ├── output/         # EnrichedSnapshot (immutable L1→L2 contract)
    ├── observability/  # OTel + Prometheus (no-op fallback)
    ├── reactor.py      # L1 Compute Reactor (main orchestrator)
    └── tests/          # pytest suite

Phase Roadmap:
    Phase 1 (Current)  — Python layer: all components
    Phase 2            — Rust ndm_rust micro-structure SIMD kernels
    Phase 3            — Arrow RecordBatch zero-copy L0→L1 handoff
"""

__version__ = "1.0.0"
