from __future__ import annotations

from l3_assembly.presenters.ui.depth_profile.window import build_contiguous_strikes


def _assert_symmetric(rows: list[float], center: float) -> None:
    for i in range(len(rows) // 2):
        assert rows[i] + rows[-1 - i] == 2 * center


def test_window_is_symmetric_around_center_without_flip() -> None:
    rows = build_contiguous_strikes(center=560.0, spacing=1.0, count=15)

    assert len(rows) == 15
    assert rows[len(rows) // 2] == 560.0
    _assert_symmetric(rows, center=560.0)


def test_even_count_is_promoted_to_odd_symmetric_window() -> None:
    rows = build_contiguous_strikes(center=560.0, spacing=1.0, count=14)

    assert len(rows) == 15
    assert rows[len(rows) // 2] == 560.0
    _assert_symmetric(rows, center=560.0)


def test_window_length_stays_fixed_when_flip_is_outside() -> None:
    rows = build_contiguous_strikes(center=560.0, spacing=1.0, count=15)

    assert len(rows) == 15
    assert rows[len(rows) // 2] == 560.0
    assert 575.0 not in rows
    _assert_symmetric(rows, center=560.0)


def test_window_length_stays_fixed_when_flip_is_inside() -> None:
    rows = build_contiguous_strikes(center=560.0, spacing=1.0, count=15)

    assert len(rows) == 15
    assert 566.0 in rows
    _assert_symmetric(rows, center=560.0)
