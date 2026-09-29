from __future__ import annotations

from types import SimpleNamespace

import pytest

from shared.services.l0_runtime.source.runtime.bootstrap import _startup_connectivity_probe


class _FakeRuntime:
    def __init__(self, rows):
        self._rows = rows
        self.calls = 0

    async def quote(self, symbols):
        assert symbols == ["SPY.US"]
        self.calls += 1
        return self._rows

    def diagnostics(self):
        return {
            "endpoint_profile": "primary",
            "endpoint_http_url": "https://openapi.longportapp.com",
        }


class _FlakyRuntime(_FakeRuntime):
    """Fails `failures` times with a transient transport error, then returns rows."""

    def __init__(self, rows, failures: int, message: str = "tls handshake eof"):
        super().__init__(rows)
        self._failures = failures
        self._message = message

    async def quote(self, symbols):
        assert symbols == ["SPY.US"]
        self.calls += 1
        if self.calls <= self._failures:
            raise RuntimeError(f"QuoteContext init failed: IO error: {self._message}")
        return self._rows


async def _probe(runtime, *, attempts: int = 3, base_sec: float = 0.0) -> float:
    return await _startup_connectivity_probe(
        runtime,
        strict_connectivity=True,
        retry_attempts=attempts,
        retry_base_sec=base_sec,
    )


@pytest.mark.asyncio
async def test_startup_connectivity_probe_returns_initial_spot() -> None:
    runtime = _FakeRuntime([SimpleNamespace(last_done="706.74")])

    spot = await _probe(runtime)

    assert spot == 706.74


@pytest.mark.asyncio
async def test_startup_connectivity_probe_rejects_non_positive_quote() -> None:
    runtime = _FakeRuntime([SimpleNamespace(last_done="0")])

    with pytest.raises(RuntimeError, match="non-positive"):
        await _probe(runtime)


@pytest.mark.asyncio
async def test_startup_connectivity_probe_does_not_retry_data_contract_failures() -> None:
    """An invalid row is an answer, not a transport fault: retrying it would be wasted work."""
    runtime = _FakeRuntime([SimpleNamespace(last_done="0")])

    with pytest.raises(RuntimeError, match="non-positive"):
        await _probe(runtime, attempts=3)

    assert runtime.calls == 1


@pytest.mark.asyncio
async def test_startup_connectivity_probe_recovers_from_transient_tls_eof() -> None:
    """The 2026-09-29 incident: two transient TLS EOFs must not kill startup."""
    runtime = _FlakyRuntime([SimpleNamespace(last_done="765.66")], failures=2)

    spot = await _probe(runtime, attempts=3, base_sec=0.0)

    assert spot == 765.66
    assert runtime.calls == 3


@pytest.mark.asyncio
async def test_single_attempt_policy_would_still_fail_on_the_same_fault() -> None:
    """Non-vacuity guard: the fix is the retry, so removing it must reproduce the outage."""
    runtime = _FlakyRuntime([SimpleNamespace(last_done="765.66")], failures=2)

    with pytest.raises(RuntimeError, match="tls handshake eof"):
        await _probe(runtime, attempts=1, base_sec=0.0)

    assert runtime.calls == 1


@pytest.mark.asyncio
async def test_startup_connectivity_probe_fails_closed_when_all_attempts_fail() -> None:
    runtime = _FlakyRuntime([SimpleNamespace(last_done="765.66")], failures=99)

    with pytest.raises(RuntimeError, match="tls handshake eof") as excinfo:
        await _probe(runtime, attempts=3, base_sec=0.0)

    assert "attempts=3" in str(excinfo.value)
    assert runtime.calls == 3


@pytest.mark.asyncio
async def test_startup_connectivity_probe_rejects_non_positive_retry_policy() -> None:
    runtime = _FakeRuntime([SimpleNamespace(last_done="706.74")])

    with pytest.raises(RuntimeError, match="longport_connect_retries"):
        await _probe(runtime, attempts=0)


@pytest.mark.asyncio
async def test_startup_connectivity_probe_rejects_negative_retry_base() -> None:
    runtime = _FakeRuntime([SimpleNamespace(last_done="706.74")])

    with pytest.raises(RuntimeError, match="longport_connect_retry_base_sec"):
        await _probe(runtime, attempts=2, base_sec=-1.0)
