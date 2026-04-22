from __future__ import annotations

import os
import socket

import pytest

from scripts.test.longport_mvp import (
    DEFAULT_CONFIG,
    FlowTick,
    FlowWindow,
    QUADRANT_PUT_ASK,
    RUN_FLAG,
    SIDE_ASK,
    SIDE_BID,
    SIDE_MID,
    SUPPRESSION_BEAR,
    SUPPRESSION_NEUTRAL,
    SuppressionStateMachine,
    classify_trade_side,
    run_live_probe,
)
from scripts.test.longport_mvp.live_probe import first_env
from scripts.test.longport_mvp.extractors import (
    exposure_delta_gamma,
    is_trade_condition_filtered,
    parse_option_type,
    tick_rule_direction,
)


def _has_longport_credentials() -> bool:
    app_key = first_env("LONGPORT_APP_KEY", "LONGBRIDGE_APP_KEY")
    app_secret = first_env("LONGPORT_APP_SECRET", "LONGBRIDGE_APP_SECRET")
    access_token = first_env("LONGPORT_ACCESS_TOKEN", "LONGBRIDGE_ACCESS_TOKEN")
    return bool(app_key and app_secret and access_token)


def _backend_is_alive() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 8001), timeout=0.5):
            return True
    except (ConnectionRefusedError, OSError):
        return False


def _skip_live_if_not_enabled() -> None:
    if os.getenv(RUN_FLAG, "0").strip() != "1":
        pytest.skip(f"set {RUN_FLAG}=1 to run live LongPort MVP test")
    if not _has_longport_credentials():
        pytest.skip("LongPort credentials are missing in environment")
    if _backend_is_alive():
        pytest.skip("backend detected on :8001; skip to avoid LongPort quota overlap")


def test_trade_side_classifier_offline_contract() -> None:
    assert parse_option_type("SPY260416C700000.US") == "CALL"
    assert parse_option_type("SPY260416P700000.US") == "PUT"
    assert parse_option_type("SPY.US") is None

    ask_side = classify_trade_side(price=3.15, bid1=3.10, ask1=3.15)
    bid_side = classify_trade_side(price=2.95, bid1=2.95, ask1=3.00)
    mid_side = classify_trade_side(price=3.02, bid1=3.00, ask1=3.05)

    assert ask_side == SIDE_ASK
    assert bid_side == SIDE_BID
    assert mid_side == SIDE_MID


def test_oi_weighted_large_flow_contract() -> None:
    flow = FlowWindow(
        window_sec=DEFAULT_CONFIG.rolling_window_sec,
        z_threshold=2.0,
        min_oi_participation=0.02,
    )
    now = 10_000.0
    for idx in range(10):
        large = flow.add(
            FlowTick(
                timestamp_mono=now + idx,
                quadrant=QUADRANT_PUT_ASK,
                score=500.0,
                oi_participation=0.05,
            )
        )
        assert not large

    low_oi_large = flow.add(
        FlowTick(
            timestamp_mono=now + 11.0,
            quadrant=QUADRANT_PUT_ASK,
            score=20_000.0,
            oi_participation=0.001,
        )
    )
    high_oi_large = flow.add(
        FlowTick(
            timestamp_mono=now + 12.0,
            quadrant=QUADRANT_PUT_ASK,
            score=30_000.0,
            oi_participation=0.05,
        )
    )
    assert not low_oi_large
    assert high_oi_large


def test_suppression_state_hold_contract() -> None:
    state = SuppressionStateMachine(dom_threshold=0.35, hold_sec=3.0)
    now = 1_000.0
    state.update(now_mono=now, bear_score=150.0, bull_score=20.0, underlying_bias=-1, micro_ret=-0.1)
    assert state.state == SUPPRESSION_NEUTRAL
    state.update(now_mono=now + 2.5, bear_score=160.0, bull_score=25.0, underlying_bias=-1, micro_ret=-0.1)
    assert state.state == SUPPRESSION_NEUTRAL
    state.update(now_mono=now + 3.2, bear_score=170.0, bull_score=20.0, underlying_bias=-1, micro_ret=-0.1)
    assert state.state == SUPPRESSION_BEAR


def test_trade_condition_filter_contract() -> None:
    assert is_trade_condition_filtered({"trade_type": "Late Print"}) is True
    assert is_trade_condition_filtered({"trade_type": "Out of Sequence"}) is True
    assert is_trade_condition_filtered({"trade_type": "Average Price"}) is True
    assert is_trade_condition_filtered({"trade_type": "Regular"}) is False


def test_tick_rule_midpoint_contract() -> None:
    assert tick_rule_direction(price=1.05, bid1=1.0, ask1=1.1, prev_price=1.00, prev_direction=0) == 1
    assert tick_rule_direction(price=1.05, bid1=1.0, ask1=1.1, prev_price=1.10, prev_direction=0) == -1
    assert tick_rule_direction(price=1.05, bid1=1.0, ask1=1.1, prev_price=1.05, prev_direction=1) == 1


def test_delta_gamma_exposure_contract() -> None:
    delta_flow, gamma_exp = exposure_delta_gamma(direction=-1, size=250.0, delta=0.42, gamma=0.03)
    assert delta_flow == pytest.approx(-10_500.0)
    assert gamma_exp == pytest.approx(750.0)


@pytest.mark.asyncio
async def test_longport_live_option_depth_trade_connectivity_mvp() -> None:
    _skip_live_if_not_enabled()
    stats = await run_live_probe(DEFAULT_CONFIG)

    assert stats.depth_events > 0, (
        f"live depth not observed in {DEFAULT_CONFIG.timeout_sec:.0f}s "
        f"(start_et={stats.start_et}, end_et={stats.end_et})"
    )
    assert stats.trade_events > 0, (
        f"live trades not observed in {DEFAULT_CONFIG.timeout_sec:.0f}s "
        f"(start_et={stats.start_et}, end_et={stats.end_et})"
    )
    assert stats.classified_total > 0, (
        f"trade-side classifier received no valid trade rows in {DEFAULT_CONFIG.timeout_sec:.0f}s "
        f"(depth_events={stats.depth_events}, trade_events={stats.trade_events}, "
        f"quadrant_hits={dict(stats.quadrant_hits)}, start_et={stats.start_et}, end_et={stats.end_et})"
    )
    assert stats.oi_enriched_events > 0, (
        f"no OI-enriched option trades in {DEFAULT_CONFIG.timeout_sec:.0f}s "
        f"(oi_symbols_cached={stats.oi_symbols_cached}, oi_backfill_batches={stats.oi_backfill_batches}, "
        f"oi_backfill_failures={stats.oi_backfill_failures}, start_et={stats.start_et}, end_et={stats.end_et})"
    )
    assert stats.oi_enriched_ratio >= DEFAULT_CONFIG.min_oi_enriched_ratio, (
        f"OI coverage too low: ratio={stats.oi_enriched_ratio:.3f} "
        f"expected>={DEFAULT_CONFIG.min_oi_enriched_ratio:.2f} "
        f"(oi_enriched_events={stats.oi_enriched_events}, classified_total={stats.classified_total}, "
        f"oi_symbols_cached={stats.oi_symbols_cached}, oi_backfill_batches={stats.oi_backfill_batches})"
    )
    assert stats.underlying_tape_samples > 0, (
        f"underlying pull-trade tape is empty in {DEFAULT_CONFIG.timeout_sec:.0f}s "
        f"(underlying_pull_failures={stats.underlying_pull_failures})"
    )
    assert stats.large_flow_hits > 0, (
        f"no large OI-weighted flow hit in {DEFAULT_CONFIG.timeout_sec:.0f}s "
        f"(large_hits_by_quadrant={dict(stats.large_hits_by_quadrant)}, "
        f"last_zscore={stats.last_zscore:.3f}, suppression_state={stats.suppression_state}, "
        f"dominance={stats.dominance_latest:.3f})"
    )
