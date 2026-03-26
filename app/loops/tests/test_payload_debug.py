from __future__ import annotations

import logging
from dataclasses import dataclass

from app.loops.payload_debug import emit_payload_debug, should_log_duplicate_payload_debug


@dataclass(frozen=True)
class _DepthRow:
    strike: float
    call_pct: float
    put_pct: float
    is_spot: bool = False
    is_flip: bool = False


@dataclass(frozen=True)
class _UiState:
    depth_profile: tuple[_DepthRow, ...]


@dataclass(frozen=True)
class _Frozen:
    ui_state: _UiState
    atm: dict[str, object] | None
    version: int
    header_volatility: dict[str, object] | None = None


def test_should_log_duplicate_payload_debug_every_30_ticks() -> None:
    assert should_log_duplicate_payload_debug(30) is True
    assert should_log_duplicate_payload_debug(31) is False


def test_emit_payload_debug_logs_depth_and_atm_summary(caplog) -> None:
    frozen = _Frozen(
        ui_state=_UiState(
            depth_profile=(
                _DepthRow(strike=657.0, call_pct=0.20, put_pct=0.10, is_spot=True),
                _DepthRow(strike=656.0, call_pct=0.15, put_pct=0.35, is_flip=True),
            ),
        ),
        atm={
            "timestamp": "2026-03-25T13:30:00-04:00",
            "straddle_pct": 0.03,
            "call_pct": 0.01,
            "put_pct": 0.02,
        },
        version=1149,
        header_volatility={
            "lookback_days": 20,
            "lookback_effective_days": 12,
            "ivr": 55.0,
            "ivp": 66.7,
            "term_structure": {
                "primary": {"ratio": 1.0345, "state": "FLAT"},
                "secondary": {"ratio": 1.1823, "state": "INVERTED"},
            },
            "iv_price_relation": {
                "state": "INVERSE_CONFIRM",
                "beta_pp_per_pct": -1.5,
            },
        },
    )

    with caplog.at_level(logging.INFO):
        emit_payload_debug(
            logging.getLogger("payload-debug-test"),
            frozen=frozen,
            tick_id=42,
            snapshot_version=1149,
            duplicate_snapshot=False,
        )

    message = caplog.messages[-2]
    assert "[L3-PAYLOAD]" in message
    assert "depth_rows=2" in message
    assert "depth_spot=657.00" in message
    assert "depth_flip=656.00" in message
    assert "atm_status=LIVE" in message
    assert "atm_straddle=0.03" in message
    header_message = caplog.messages[-1]
    assert "header_volatility" in header_message
    assert "lookback=20" in header_message
    assert "ivr=55.0000" in header_message
    assert "term_1d_state=FLAT" in header_message
    assert "relation_state=INVERSE_CONFIRM" in header_message
