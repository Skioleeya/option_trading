from __future__ import annotations

from datetime import datetime
from pathlib import Path
import uuid
from zoneinfo import ZoneInfo

import pytest

from l1_compute.trackers.wall_migration_tracker import WallMigrationTracker
from shared.config import settings
from shared.models.microstructure import (
    WallMigrationCallState,
    WallMigrationPutState,
    WallMigrationResult,
)


ET = ZoneInfo("US/Eastern")


def _next_tick(ts: float) -> float:
    return ts + float(settings.wall_snapshot_interval_seconds) + 1.0


def _mk_cold_dir() -> Path:
    root = Path("tmp/pytest_cache/wall_migration_tests")
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"wall_migration_{uuid.uuid4().hex[:10]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_zero_wall_levels_do_not_trigger_false_breach() -> None:
    tracker = WallMigrationTracker()
    t0 = 1000.0

    tracker.update(call_wall=0.0, put_wall=0.0, spot=620.0, sim_clock_mono=t0)
    result = tracker.update(
        call_wall=0.0,
        put_wall=0.0,
        spot=620.0,
        sim_clock_mono=_next_tick(t0),
    )

    assert result.call_wall_state != WallMigrationCallState.BREACHED
    assert result.put_wall_state != WallMigrationPutState.BREACHED
    assert all(v is None for v in result.call_wall_history)
    assert all(v is None for v in result.put_wall_history)


def test_valid_call_wall_can_still_breach() -> None:
    tracker = WallMigrationTracker()
    t0 = 2000.0

    tracker.update(call_wall=600.0, put_wall=580.0, spot=610.0, sim_clock_mono=t0)
    result = tracker.update(
        call_wall=600.0,
        put_wall=580.0,
        spot=610.0,
        sim_clock_mono=_next_tick(t0),
    )

    assert result.call_wall_state == WallMigrationCallState.BREACHED
    assert result.call_wall_history[-1] == 600.0


def test_persistence_restores_recent_window_after_restart() -> None:
    cold_root = _mk_cold_dir()
    t0 = 3000.0
    day = datetime(2026, 3, 9, 10, 0, 0, tzinfo=ET)

    tracker = WallMigrationTracker(cold_storage_root=str(cold_root), snapshot_window=10)
    tracker.update(call_wall=600.0, put_wall=580.0, spot=590.0, sim_clock_mono=t0, sim_now_et=day)
    tracker.update(
        call_wall=601.0,
        put_wall=579.0,
        spot=590.0,
        sim_clock_mono=_next_tick(t0),
        sim_now_et=day,
    )

    tracker_restarted = WallMigrationTracker(cold_storage_root=str(cold_root), snapshot_window=10)
    result = tracker_restarted.update(
        call_wall=602.0,
        put_wall=578.0,
        spot=590.0,
        sim_clock_mono=_next_tick(_next_tick(t0)),
        sim_now_et=day,
    )

    assert any(v == 600.0 for v in result.call_wall_history)
    assert result.call_wall_history[-1] == 602.0


def test_date_rollover_isolates_history_files() -> None:
    cold_root = _mk_cold_dir()
    t0 = 4000.0
    day1 = datetime(2026, 3, 9, 10, 0, 0, tzinfo=ET)
    day2 = datetime(2026, 3, 10, 10, 0, 0, tzinfo=ET)

    tracker = WallMigrationTracker(cold_storage_root=str(cold_root), snapshot_window=10)
    tracker.update(call_wall=610.0, put_wall=585.0, spot=595.0, sim_clock_mono=t0, sim_now_et=day1)
    tracker.update(
        call_wall=611.0,
        put_wall=584.0,
        spot=595.0,
        sim_clock_mono=_next_tick(t0),
        sim_now_et=day1,
    )

    result = tracker.update(
        call_wall=620.0,
        put_wall=590.0,
        spot=600.0,
        sim_clock_mono=_next_tick(_next_tick(t0)),
        sim_now_et=day2,
    )

    assert result.call_wall_history[-1] == 620.0
    assert 611.0 not in result.call_wall_history
    assert (cold_root / "wall_series_20260309.jsonl").exists()
    assert (cold_root / "wall_series_20260310.jsonl").exists()


def test_storage_failure_does_not_break_update(monkeypatch) -> None:
    tracker = WallMigrationTracker(cold_storage_root=str(_mk_cold_dir()), snapshot_window=10)
    assert tracker._storage is not None  # noqa: SLF001 - intentional fault injection

    def _raise_on_append(*args, **kwargs) -> None:
        raise OSError("disk unavailable")

    monkeypatch.setattr(tracker._storage, "append_snapshot", _raise_on_append)  # noqa: SLF001

    result = tracker.update(
        call_wall=600.0,
        put_wall=580.0,
        spot=590.0,
        sim_clock_mono=5000.0,
        sim_now_et=datetime(2026, 3, 9, 10, 0, 0, tzinfo=ET),
    )
    assert isinstance(result, WallMigrationResult)
