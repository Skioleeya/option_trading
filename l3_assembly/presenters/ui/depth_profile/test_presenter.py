from __future__ import annotations

from l3_assembly.presenters.ui.depth_profile import presenter
from l3_assembly.presenters.ui.depth_profile.presenter import DepthProfilePresenter
from l3_assembly.presenters.ui.depth_profile.window import build_contiguous_strikes


def _reset_state() -> None:
    presenter._prev_calls = None
    presenter._prev_puts = None
    presenter._center_ema = 0.0
    presenter._ema_max_gex = 0.0
    presenter._current_ema_date = ""


def _sample_chain() -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for strike in range(530, 591):
        rows.append(
            {
                "strike": float(strike),
                "call_gex": 1.0 + (strike % 7) * 0.1,
                "put_gex": 1.0 + (strike % 5) * 0.1,
                "toxicity_score": 0.0,
                "bbo_imbalance": 0.0,
            }
        )
    return rows


def test_presenter_handles_expanded_window_without_overflow() -> None:
    _reset_state()
    out = DepthProfilePresenter.build(_sample_chain(), spot=560.0, flip_level=580.0)
    expected_strikes = build_contiguous_strikes(
        center=560.0,
        spacing=1.0,
        count=15,
    )

    assert len(out) == len(expected_strikes)
    assert len(out) == 15
    strikes = [row["strike"] for row in out]
    assert strikes[len(strikes) // 2] == 560.0
    assert strikes == sorted(strikes, reverse=True)
    assert 580.0 not in strikes
    assert not any(row["is_flip"] for row in out)


def test_presenter_row_count_stays_fixed_across_flip_levels() -> None:
    _reset_state()
    outer = DepthProfilePresenter.build(_sample_chain(), spot=560.0, flip_level=580.0)
    inner = DepthProfilePresenter.build(_sample_chain(), spot=560.0, flip_level=562.0)

    assert len(outer) == 15
    assert len(inner) == 15
    assert any(row["is_flip"] for row in inner)
