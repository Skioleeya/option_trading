from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.loops.compute_loop import _build_l1_extra_metadata, _normalize_source_timestamp_utc


def test_normalize_source_timestamp_prefers_as_of_utc():
    snapshot = {
        "as_of_utc": "2026-03-06T14:30:00+00:00",
        "as_of": datetime(2026, 3, 6, 9, 30, 0, tzinfo=ZoneInfo("US/Eastern")),
    }
    assert _normalize_source_timestamp_utc(snapshot) == "2026-03-06T14:30:00+00:00"


def test_normalize_source_timestamp_falls_back_to_as_of_datetime():
    snapshot = {
        "as_of": datetime(2026, 3, 6, 9, 30, 0, tzinfo=ZoneInfo("US/Eastern")),
    }
    assert _normalize_source_timestamp_utc(snapshot) == "2026-03-06T14:30:00+00:00"


def test_normalize_source_timestamp_handles_naive_as_of_as_utc():
    snapshot = {
        "as_of": datetime(2026, 3, 6, 14, 30, 0),
    }
    assert _normalize_source_timestamp_utc(snapshot) == "2026-03-06T14:30:00+00:00"


def test_build_l1_extra_metadata_includes_source_timestamp_and_volume_map():
    snapshot = {
        "as_of_utc": "2026-03-06T14:30:00+00:00",
        "rust_active": True,
        "shm_stats": {"status": "OK"},
        "volume_map": {"560": 1200, "bad": "x"},
    }
    out = _build_l1_extra_metadata(snapshot)

    assert out["source_data_timestamp_utc"] == "2026-03-06T14:30:00+00:00"
    assert out["rust_active"] is True
    assert out["shm_stats"] == {"status": "OK"}
    assert out["volume_map"] == {"560": 1200.0}


def test_build_l1_extra_metadata_source_timestamp_none_when_invalid():
    snapshot = {
        "as_of_utc": "not-a-time",
        "as_of": object(),
    }
    out = _build_l1_extra_metadata(snapshot)
    assert out["source_data_timestamp_utc"] is None
