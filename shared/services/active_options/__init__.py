"""Shared neutral ActiveOptions runtime services.

This package is cross-layer safe and can be imported by app/l2/l3.
"""

from .constants import (
    ACTIVE_OPTIONS_CHARM_SURGE_END_HOUR_ET,
    ACTIVE_OPTIONS_CHARM_SURGE_START_HOUR_ET,
    ACTIVE_OPTIONS_DEFAULT_LIMIT,
    ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_MILLION,
    ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_THOUSAND,
    ACTIVE_OPTIONS_FLOW_ZSCORE_ROUND_DIGITS,
    ACTIVE_OPTIONS_PLACEHOLDER_SIGNATURE_PREFIX,
    ACTIVE_OPTIONS_SIGNATURE_STRIKE_ROUND_DIGITS,
    ACTIVE_OPTIONS_SWITCH_CONFIRM_TICKS,
)
from .flow_engine_d import FlowEngineD
from .flow_engine_e import FlowEngineE
from .flow_engine_g import FlowEngineG
from .deg_composer import DEGComposer, InstitutionalSweepDetector
from .input_adapter import (
    ACTIVE_OPTIONS_INPUT_REASON_EMPTY_CHAIN,
    ACTIVE_OPTIONS_INPUT_REASON_INVALID_SPOT,
    ActiveOptionsInputSnapshotData,
    build_active_options_input_snapshot,
)
from .runtime_service import ActiveOptionsRuntimeService

__all__ = [
    "ACTIVE_OPTIONS_DEFAULT_LIMIT",
    "ACTIVE_OPTIONS_SWITCH_CONFIRM_TICKS",
    "ACTIVE_OPTIONS_CHARM_SURGE_START_HOUR_ET",
    "ACTIVE_OPTIONS_CHARM_SURGE_END_HOUR_ET",
    "ACTIVE_OPTIONS_PLACEHOLDER_SIGNATURE_PREFIX",
    "ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_MILLION",
    "ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_THOUSAND",
    "ACTIVE_OPTIONS_FLOW_ZSCORE_ROUND_DIGITS",
    "ACTIVE_OPTIONS_SIGNATURE_STRIKE_ROUND_DIGITS",
    "FlowEngineD",
    "FlowEngineE",
    "FlowEngineG",
    "DEGComposer",
    "InstitutionalSweepDetector",
    "ACTIVE_OPTIONS_INPUT_REASON_EMPTY_CHAIN",
    "ACTIVE_OPTIONS_INPUT_REASON_INVALID_SPOT",
    "ActiveOptionsInputSnapshotData",
    "build_active_options_input_snapshot",
    "ActiveOptionsRuntimeService",
]
