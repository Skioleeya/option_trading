from shared.contracts.metric_semantics import get_metric_semantics, iter_metric_semantics
from shared.system.tactical_triad_logic import (
    compute_guard_vrp_proxy_pct,
    normalize_guard_vrp_threshold_pct,
)


def test_registry_contains_phase_e_required_metrics() -> None:
    required = {
        "net_gex",
        "zero_gamma_level",
        "call_wall",
        "put_wall",
        "flip_level_cumulative",
        "FLOW_D",
        "FLOW_E",
        "FLOW_G",
        "vol_risk_premium",
        "guard_vrp_proxy_pct",
        "skew_25d_normalized",
        "rr25_call_minus_put",
        "net_charm_raw_sum",
        "net_vanna_raw_sum",
    }
    names = {item.metric_name for item in iter_metric_semantics()}
    assert required.issubset(names)


def test_registry_entries_expose_required_fields() -> None:
    semantics = get_metric_semantics("net_gex")
    assert semantics.metric_name == "net_gex"
    assert semantics.classification in {"academic_standard", "proxy", "heuristic"}
    assert semantics.unit
    assert semantics.sign_convention
    assert semantics.data_prerequisites
    assert semantics.canonical_description
    assert semantics.live_usage in {"live", "research", "legacy-only"}


def test_unknown_metric_lookup_raises_keyerror() -> None:
    try:
        get_metric_semantics("unknown_metric")
    except KeyError:
        return
    raise AssertionError("Expected KeyError for unknown metric lookup")


def test_guard_threshold_normalization_supports_legacy_decimal_inputs() -> None:
    assert normalize_guard_vrp_threshold_pct(0.15, 15.0) == 15.0
    assert normalize_guard_vrp_threshold_pct(0.13, 13.0) == 13.0
    assert normalize_guard_vrp_threshold_pct(15.0, 15.0) == 15.0
    assert normalize_guard_vrp_threshold_pct(13.0, 13.0) == 13.0


def test_guard_vrp_proxy_pct_uses_percent_point_contract() -> None:
    # 0.18 => 18.0%; |vol_accel_ratio|=0.2 => realized proxy 2.0%
    assert compute_guard_vrp_proxy_pct(0.18, 0.2) == 16.0
    # Already-percent ATM IV path should produce the same value.
    assert compute_guard_vrp_proxy_pct(18.0, 0.2) == 16.0
