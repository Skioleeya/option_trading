"""l3_refactor.presenters — Presenter V2 wrappers (strong-typed output).

Each presenter wraps the existing legacy presenter logic and returns
a typed frozen dataclass instead of dict[str, Any].

All V2 presenters provide:
    build(...)  → frozen dataclass
    to_dict()   → dict compatible with legacy SnapshotBuilder output

Migration strategy:
    V2 presenters call the SAME computation logic as legacy presenters.
    Only the output type contract changes. This is a Strangler Fig on the
    presenter boundary, not a rewrite.
"""

from l3_refactor.presenters.micro_stats import MicroStatsPresenterV2
from l3_refactor.presenters.tactical_triad import TacticalTriadPresenterV2
from l3_refactor.presenters.wall_migration import WallMigrationPresenterV2
from l3_refactor.presenters.depth_profile import DepthProfilePresenterV2
from l3_refactor.presenters.active_options import ActiveOptionsPresenterV2
from l3_refactor.presenters.mtf_flow import MTFFlowPresenterV2
from l3_refactor.presenters.skew_dynamics import SkewDynamicsPresenterV2

__all__ = [
    "MicroStatsPresenterV2",
    "TacticalTriadPresenterV2",
    "WallMigrationPresenterV2",
    "DepthProfilePresenterV2",
    "ActiveOptionsPresenterV2",
    "MTFFlowPresenterV2",
    "SkewDynamicsPresenterV2",
]
