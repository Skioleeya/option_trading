from __future__ import annotations

from l1_compute.trackers.wall_migration_tracker import WallMigrationTracker
from shared.config import settings
from shared.models.microstructure import (
    WallMigrationCallState,
    WallMigrationPutState,
)


def _next_tick(ts: float) -> float:
    return ts + float(settings.wall_snapshot_interval_seconds) + 1.0


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
