from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from infra.ops_cli import start_backend as mod


def test_graceful_stop_existing_backend_asks_then_confirms_exit(monkeypatch) -> None:
    """Stop-Process without -Force is the graceful request; no force kill when it works."""
    states = [[1111], []]
    scripts: list[str] = []

    monkeypatch.setattr(mod, "_backend_pids", lambda: states.pop(0) if states else [])
    monkeypatch.setattr(mod, "_run_powershell", lambda script: scripts.append(script))
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)

    stopped, remaining = mod._graceful_stop_existing_backend(0.5)

    assert stopped is True
    assert remaining == []
    assert scripts == ["Stop-Process -Id 1111 -ErrorAction SilentlyContinue"]


def test_graceful_stop_existing_backend_force_kills_when_it_will_not_exit(monkeypatch) -> None:
    scripts: list[str] = []
    clock = iter([0.0, 1.0])

    monkeypatch.setattr(mod, "_backend_pids", lambda: [2222])
    monkeypatch.setattr(mod, "_run_powershell", lambda script: scripts.append(script))
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)
    monkeypatch.setattr(mod.time, "time", lambda: next(clock))

    stopped, remaining = mod._graceful_stop_existing_backend(0.5)

    assert stopped is False
    assert remaining == [2222]
    assert scripts == [
        "Stop-Process -Id 2222 -ErrorAction SilentlyContinue",
        "Stop-Process -Id 2222 -Force -ErrorAction SilentlyContinue",
    ]


def test_run_start_backend_fails_when_existing_backend_wont_exit(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(mod, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(mod, "_graceful_stop_existing_backend", lambda _timeout: (False, [2222]))
    monkeypatch.setattr(mod.os, "chdir", lambda _: None)

    args = Namespace(
        bind_host="0.0.0.0",
        port=8001,
        degraded=False,
        hotfix_active_options=False,
        hotfix_min_volume=10,
        log_file=None,
        foreground=False,
        dry_run=False,
        shutdown_timeout_sec=5.0,
    )

    assert mod.run_start_backend(args) == 1
