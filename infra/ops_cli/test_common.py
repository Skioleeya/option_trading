from __future__ import annotations

from pathlib import Path

import pytest

from infra.ops_cli.common import read_tail_lines


def test_read_tail_lines_returns_last_lines(tmp_path: Path) -> None:
    path = tmp_path / "runtime.log"
    path.write_text("".join(f"line-{i}\n" for i in range(500)), encoding="utf-8")

    assert read_tail_lines(path, 3) == ["line-497", "line-498", "line-499"]


def test_read_tail_lines_returns_all_when_file_smaller_than_window(tmp_path: Path) -> None:
    path = tmp_path / "runtime.log"
    path.write_text("alpha\nbeta\n", encoding="utf-8")

    assert read_tail_lines(path, 40) == ["alpha", "beta"]


def test_read_tail_lines_missing_file_returns_empty(tmp_path: Path) -> None:
    assert read_tail_lines(tmp_path / "absent.log", 40) == []


def test_read_tail_lines_does_not_scan_from_the_start(tmp_path: Path) -> None:
    """A 1 MiB first line must never surface when the window is 4 KiB.

    This is the regression guard for the start-all freeze: the old
    ``read_text().splitlines()[-40:]`` materialised the whole file, so the
    head of the log always ended up in the parsed list.
    """
    path = tmp_path / "runtime.log"
    payload = b"X" * (1024 * 1024) + b"\n" + b"".join(b"tail-%d\n" % i for i in range(500))
    path.write_bytes(payload)

    lines = read_tail_lines(path, 10, max_bytes=4096)

    assert lines[-1] == "tail-499"
    assert len(lines) == 10
    assert all("X" not in line for line in lines)


def test_read_tail_lines_drops_truncated_leading_fragment(tmp_path: Path) -> None:
    """The first entry of a mid-file byte window is a fragment and must be discarded."""
    path = tmp_path / "runtime.log"
    path.write_bytes(b"AAAAAAAAAA\nBBBBBBBBBB\nCCCCCCCCCC\nDDDDDDDDDD\n")

    lines = read_tail_lines(path, 2, max_bytes=25)

    assert lines == ["CCCCCCCCCC", "DDDDDDDDDD"]


def test_read_tail_lines_window_smaller_than_requested_line_count(tmp_path: Path) -> None:
    """Bounded work wins: a narrow window yields fewer than ``max_lines`` complete lines."""
    path = tmp_path / "runtime.log"
    path.write_bytes(b"AAAAAAAAAA\nBBBBBBBBBB\nCCCCCCCCCC\nDDDDDDDDDD\n")

    assert read_tail_lines(path, 40, max_bytes=25) == ["CCCCCCCCCC", "DDDDDDDDDD"]


def test_read_tail_lines_matches_naive_tail_on_large_file(tmp_path: Path) -> None:
    """Fidelity: identical output to the naive implementation it replaced."""
    path = tmp_path / "runtime.log"
    path.write_text("".join(f"2026-09-25 row {i}\n" for i in range(20000)), encoding="utf-8")

    naive = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-40:]
    assert read_tail_lines(path, 40) == naive


@pytest.mark.parametrize(("max_lines", "max_bytes"), [(0, 1024), (-1, 1024), (10, 0), (10, -5)])
def test_read_tail_lines_rejects_non_positive_bounds(
    tmp_path: Path, max_lines: int, max_bytes: int
) -> None:
    path = tmp_path / "runtime.log"
    path.write_text("one\ntwo\n", encoding="utf-8")

    with pytest.raises(ValueError):
        read_tail_lines(path, max_lines, max_bytes=max_bytes)
