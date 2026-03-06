from __future__ import annotations

from app.loops.compute_loop import _extract_snapshot_version


def test_extract_snapshot_version_accepts_int() -> None:
    assert _extract_snapshot_version({"version": 42}) == 42


def test_extract_snapshot_version_accepts_float() -> None:
    assert _extract_snapshot_version({"version": 42.9}) == 42


def test_extract_snapshot_version_accepts_numeric_string() -> None:
    assert _extract_snapshot_version({"version": "123"}) == 123


def test_extract_snapshot_version_rejects_invalid_values() -> None:
    assert _extract_snapshot_version({}) == 0
    assert _extract_snapshot_version({"version": None}) == 0
    assert _extract_snapshot_version({"version": "bad"}) == 0
    assert _extract_snapshot_version({"version": True}) == 0
