from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from infra.ops_cli import log_layout


def test_trading_date_iso_uses_new_york_calendar() -> None:
    # 2026-09-29 01:30 UTC == 2026-09-28 21:30 EDT -> still the previous trading date.
    moment = datetime(2026, 9, 29, 1, 30, tzinfo=ZoneInfo("UTC"))

    assert log_layout.trading_date_iso(moment) == "2026-09-28"


def test_allocate_run_log_path_creates_dated_service_slot(tmp_path: Path) -> None:
    path = log_layout.allocate_run_log_path(
        tmp_path,
        log_layout.SERVICE_BACKEND,
        date_iso="2026-09-29",
    )

    assert path == tmp_path / "logs" / "2026-09-29" / "backend" / "run-001.log"
    assert path.exists()


def test_allocate_run_log_path_increments_per_service(tmp_path: Path) -> None:
    first = log_layout.allocate_run_log_path(tmp_path, "backend", date_iso="2026-09-29")
    second = log_layout.allocate_run_log_path(tmp_path, "backend", date_iso="2026-09-29")
    other = log_layout.allocate_run_log_path(tmp_path, "frontend", date_iso="2026-09-29")

    assert first.name == "run-001.log"
    assert second.name == "run-002.log"
    # Start ordinals are per service, not shared across the stack.
    assert other.name == "run-001.log"
    assert other.parent.parent.name == "2026-09-29"


def test_allocate_run_log_path_isolates_dates(tmp_path: Path) -> None:
    day_one = log_layout.allocate_run_log_path(tmp_path, "backend", date_iso="2026-09-28")
    day_two = log_layout.allocate_run_log_path(tmp_path, "backend", date_iso="2026-09-29")

    assert day_one.parent != day_two.parent
    assert day_one.name == "run-001.log"
    assert day_two.name == "run-001.log"


def test_allocate_run_log_path_never_reuses_an_existing_run(tmp_path: Path) -> None:
    """Ordinals only move forward: an old run's file must stay untouched."""
    directory = tmp_path / "logs" / "2026-09-29" / "backend"
    directory.mkdir(parents=True)
    existing = directory / "run-004.log"
    existing.write_text("previous run\n", encoding="utf-8")

    path = log_layout.allocate_run_log_path(tmp_path, "backend", date_iso="2026-09-29")

    assert path.name == "run-005.log"
    assert existing.read_text(encoding="utf-8") == "previous run\n"


def test_allocate_run_log_path_skips_a_taken_ordinal(tmp_path: Path) -> None:
    directory = tmp_path / "logs" / "2026-09-29" / "backend"
    directory.mkdir(parents=True)
    (directory / "run-001.log").write_text("x", encoding="utf-8")
    (directory / "run-003.log").write_text("x", encoding="utf-8")

    path = log_layout.allocate_run_log_path(tmp_path, "backend", date_iso="2026-09-29")

    assert path.name == "run-004.log"


def test_allocate_run_log_path_respects_custom_root(tmp_path: Path) -> None:
    path = log_layout.allocate_run_log_path(
        tmp_path,
        "backend",
        log_root="var/logs",
        date_iso="2026-09-29",
    )

    assert path == tmp_path / "var" / "logs" / "2026-09-29" / "backend" / "run-001.log"


@pytest.mark.parametrize(
    ("service", "log_root", "date_iso"),
    [
        ("nope", "logs", "2026-09-29"),
        ("backend", "", "2026-09-29"),
        ("backend", "logs", ""),
    ],
)
def test_service_dir_rejects_bad_inputs(service: str, log_root: str, date_iso: str) -> None:
    with pytest.raises(ValueError):
        log_layout.service_dir(Path("."), service, log_root=log_root, date_iso=date_iso)
