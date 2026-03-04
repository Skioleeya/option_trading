"""l2_refactor — L2 Decision & Analysis Layer Refactoring Package.

Strangler Fig 模式 — 与 backend/app/agents/ 并存，验证通过后逐步替换。

Pipeline:
    EnrichedSnapshot (L1) → FeatureStore → SignalGenerators
    → FusionEngine → GuardRails → DecisionOutput (L2)

Entry point:
    from l2_refactor.reactor import L2DecisionReactor
"""

from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["L2DecisionReactor"]
