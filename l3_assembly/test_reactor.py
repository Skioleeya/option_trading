"""Tests for L3AssemblyReactor research-persistence retry policy.

Regression guard for the 2026-09-24 incident: a transient Windows
``ReplaceFileW`` failure (WinError 1175) on the canonical parquet hard-stopped
the entire L3 broadcast loop on the very first attempt, which in turn froze the
Redis warm tier and left the UI showing ``RDS STALLED``.
"""

from __future__ import annotations

from typing import Any

import pytest

from l3_assembly.reactor import L3AssemblyReactor, ResearchPersistenceFatalError
from shared.config import settings


class _FlakyResearchStore:
    """``append_tick`` that fails a fixed number of times before succeeding."""

    def __init__(self, failures_before_success: int) -> None:
        self._remaining_failures = failures_before_success
        self.calls = 0

    def append_tick(self, *, decision: Any, snapshot: Any, payload: Any) -> None:
        self.calls += 1
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise OSError("Unable to remove the file to be replaced. (os error 1175)")


def _reactor_with(store: _FlakyResearchStore) -> L3AssemblyReactor:
    """Build a reactor without running ``__init__`` (no Redis / real store I/O)."""
    reactor = object.__new__(L3AssemblyReactor)
    reactor.research_store = store
    reactor._research_persistence_fatal = None
    return reactor


def _append(reactor: L3AssemblyReactor) -> None:
    reactor._append_research_tick(decision=None, snapshot=None, payload=None)


@pytest.fixture(autouse=True)
def _no_retry_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "research_persist_retry_delay_ms", 0)


def test_transient_replace_failure_is_retried_and_recovers() -> None:
    store = _FlakyResearchStore(failures_before_success=2)
    reactor = _reactor_with(store)

    _append(reactor)

    assert store.calls == 3
    assert reactor._research_persistence_fatal is None


def test_retry_budget_exhaustion_is_still_fatal() -> None:
    store = _FlakyResearchStore(failures_before_success=99)
    reactor = _reactor_with(store)

    with pytest.raises(ResearchPersistenceFatalError):
        _append(reactor)

    assert store.calls == settings.research_persist_max_attempts
    assert reactor._research_persistence_fatal is not None


def test_single_attempt_budget_fails_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation guard: pinning the budget to 1 must reproduce the pre-fix behaviour."""
    monkeypatch.setattr(settings, "research_persist_max_attempts", 1)
    store = _FlakyResearchStore(failures_before_success=1)
    reactor = _reactor_with(store)

    with pytest.raises(ResearchPersistenceFatalError):
        _append(reactor)

    assert store.calls == 1


def test_fatal_state_short_circuits_further_ticks() -> None:
    store = _FlakyResearchStore(failures_before_success=0)
    reactor = _reactor_with(store)
    reactor._research_persistence_fatal = "OSError: boom"

    with pytest.raises(ResearchPersistenceFatalError):
        _append(reactor)

    assert store.calls == 0
