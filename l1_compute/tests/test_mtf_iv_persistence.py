from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import uuid
from zoneinfo import ZoneInfo

from l1_compute.analysis.mtf_iv_engine import MTFIVEngine
from l1_compute.trackers.mtf_iv_persistence import MTFIVWindowPersistence
from l1_compute.trackers.mtf_iv_window_storage import MTFIVWindowStorage


ET = ZoneInfo("US/Eastern")


def _mk_cold_dir() -> Path:
    root = Path("tmp/pytest_cache/mtf_iv_tests")
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"mtf_iv_{uuid.uuid4().hex[:10]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _seed_engine(engine: MTFIVEngine) -> None:
    for i in range(6):
        engine.update("1m", 0.200 + i * 0.001)
        engine.update("5m", 0.220 + i * 0.001)
        engine.update("15m", 0.240 + i * 0.001)


def test_persistence_restores_windows_after_restart() -> None:
    cold_root = _mk_cold_dir()
    day = datetime(2026, 3, 9, 10, 0, 0, tzinfo=ET)

    engine = MTFIVEngine()
    persistence = MTFIVWindowPersistence(cold_storage_root=str(cold_root))
    date_str = persistence.bootstrap_day(now_et=day, engine=engine)
    _seed_engine(engine)
    persistence.persist_snapshot(date_str=date_str, now_et=day, engine=engine)

    restarted_engine = MTFIVEngine()
    restarted_persistence = MTFIVWindowPersistence(cold_storage_root=str(cold_root))
    restarted_persistence.bootstrap_day(now_et=day, engine=restarted_engine)

    assert restarted_engine.export_state() == engine.export_state()
    mtf = restarted_engine.compute({"1m": 0.25, "5m": 0.25, "15m": 0.25})
    assert mtf["timeframes"]["1m"]["regime"] != "UNAVAILABLE"
    assert mtf["timeframes"]["5m"]["regime"] != "UNAVAILABLE"
    assert mtf["timeframes"]["15m"]["regime"] != "UNAVAILABLE"


def test_date_rollover_resets_windows_and_isolates_files() -> None:
    cold_root = _mk_cold_dir()
    day1 = datetime(2026, 3, 9, 10, 0, 0, tzinfo=ET)
    day2 = datetime(2026, 3, 10, 10, 0, 0, tzinfo=ET)

    engine = MTFIVEngine()
    persistence = MTFIVWindowPersistence(cold_storage_root=str(cold_root))

    date1 = persistence.bootstrap_day(now_et=day1, engine=engine)
    _seed_engine(engine)
    persistence.persist_snapshot(date_str=date1, now_et=day1, engine=engine)

    date2 = persistence.bootstrap_day(now_et=day2, engine=engine)
    cleared = engine.export_state()
    assert all(len(v) == 0 for v in cleared.values())

    engine.update("1m", 0.30)
    persistence.persist_snapshot(date_str=date2, now_et=day2, engine=engine)

    assert (cold_root / "mtf_iv_series_20260309.jsonl").exists()
    assert (cold_root / "mtf_iv_series_20260310.jsonl").exists()


def test_storage_failure_does_not_break_engine_compute(monkeypatch) -> None:
    cold_root = _mk_cold_dir()
    day = datetime(2026, 3, 9, 10, 0, 0, tzinfo=ET)

    engine = MTFIVEngine()
    persistence = MTFIVWindowPersistence(cold_storage_root=str(cold_root))
    date_str = persistence.bootstrap_day(now_et=day, engine=engine)
    _seed_engine(engine)

    assert persistence._storage is not None  # noqa: SLF001 - intentional fault injection

    def _raise_on_append(*args, **kwargs) -> None:
        raise OSError("disk unavailable")

    monkeypatch.setattr(persistence._storage, "append_snapshot", _raise_on_append)  # noqa: SLF001
    persistence.persist_snapshot(date_str=date_str, now_et=day, engine=engine)

    mtf = engine.compute({"1m": 0.25, "5m": 0.25, "15m": 0.25})
    assert "timeframes" in mtf
    assert "consensus" in mtf


def test_storage_sanitizes_bad_rows_without_polluting_windows() -> None:
    cold_root = _mk_cold_dir()
    storage = MTFIVWindowStorage(cold_root)
    path = cold_root / "mtf_iv_series_20260309.jsonl"

    with path.open("w", encoding="utf-8") as fh:
        fh.write("{bad json}\n")
        fh.write(json.dumps({
            "timestamp": "2026-03-09T10:00:00-05:00",
            "windows": {
                "1m": [0.2, "x", -1, float("nan")],
                "5m": [0.3],
                "15m": [],
            },
        }))
        fh.write("\n")
        fh.write(json.dumps({
            "timestamp": "2026-03-09T10:00:01-05:00",
            "windows": {"1m": [], "5m": [], "15m": []},
        }))
        fh.write("\n")

    rows = storage.load_recent("20260309", 10)
    assert len(rows) == 1
    assert rows[0]["windows"]["1m"] == [0.2]
    assert rows[0]["windows"]["5m"] == [0.3]
    assert rows[0]["windows"]["15m"] == []
