from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from infra.ops_cli import start_backend as mod


def test_graceful_stop_existing_backend_sends_sigterm_and_waits(monkeypatch) -> None:
    states = [[1111], []]
    sent: list[tuple[int, int]] = []

    monkeypatch.setattr(mod, "_backend_pids", lambda: states.pop(0) if states else [])
    monkeypatch.setattr(mod.os, "kill", lambda pid, sig: sent.append((pid, sig)))
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)

    stopped, remaining = mod._graceful_stop_existing_backend(0.5)

    assert stopped is True
    assert remaining == []
    assert sent == [(1111, mod.signal.SIGTERM)]


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
        log_file="logs/backend_runtime.current.log",
        foreground=False,
        dry_run=False,
        shutdown_timeout_sec=5.0,
    )

    assert mod.run_start_backend(args) == 1
