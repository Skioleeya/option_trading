from __future__ import annotations

import asyncio
import threading
import time

import pytest

from shared.services.l0_runtime.source.runtime.quote_runtime import RustQuoteRuntime


class _FakeGateway:
    def __init__(self) -> None:
        self.starts: list[list[str]] = []
        self.subscribes: list[list[str]] = []
        self.unsubscribes: list[list[str]] = []
        self.diagnostics_calls = 0

    def start(
        self,
        symbols: list[str],
        shm_path: str,
        cpu_id: int,
        batch_interval_ms: int,
        batch_max_rows: int,
        shm_capacity_bytes: int,
        signal_name: str,
    ) -> None:
        del shm_path, cpu_id, batch_interval_ms, batch_max_rows, shm_capacity_bytes, signal_name
        self.starts.append(list(symbols))

    def subscribe(self, symbols: list[str]) -> None:
        self.subscribes.append(list(symbols))

    def unsubscribe(self, symbols: list[str]) -> None:
        self.unsubscribes.append(list(symbols))

    def diagnostics_handle(self) -> "_FakeDiagnosticsHandle":
        return _FakeDiagnosticsHandle(self)


class _FakeDiagnosticsHandle:
    def __init__(self, gateway: _FakeGateway) -> None:
        self._gateway = gateway

    def snapshot(self) -> dict[str, object]:
        self._gateway.diagnostics_calls += 1
        return {
            "raw_quote_event_count_1s": 9,
            "raw_depth_event_count_1s": 3,
            "last_raw_quote_gap_ms": 110.0,
            "last_raw_depth_gap_ms": 455.0,
        }


@pytest.mark.asyncio
async def test_rust_quote_runtime_reconciles_symbol_deltas(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = RustQuoteRuntime(_config=object())
    gateway = _FakeGateway()
    runtime._gateway = gateway

    async def _execute_inline(_op_name: str, operation):
        return operation(gateway)

    monkeypatch.setattr(runtime, "_execute", _execute_inline)

    await runtime.subscribe(["SPY.US", "OPT_A"])
    await runtime.subscribe(["SPY.US", "OPT_B"])

    assert gateway.starts == [["OPT_A", "SPY.US"]]
    assert gateway.subscribes == [["OPT_B"]]
    assert gateway.unsubscribes == [["OPT_A"]]


def test_rust_quote_runtime_diagnostics_include_gateway_raw_counters() -> None:
    runtime = RustQuoteRuntime(_config=object())
    gateway = _FakeGateway()
    runtime._gateway = gateway
    runtime._gateway_diag_handle = gateway.diagnostics_handle()
    runtime._connected = True
    runtime._started = True
    runtime._symbols = {"SPY.US", "OPT_A"}
    runtime._endpoint_profiles = [{"name": "official_longbridge", "http_url": "https://api.example"}]

    diag = runtime.diagnostics()

    assert diag["connected"] is True
    assert diag["rust_started"] is True
    assert diag["tracked_symbols"] == 2
    assert diag["endpoint_profile"] == "official_longbridge"
    assert diag["raw_quote_event_count_1s"] == 9
    assert diag["raw_depth_event_count_1s"] == 3
    assert diag["last_raw_quote_gap_ms"] == 110.0
    assert diag["last_raw_depth_gap_ms"] == 455.0
    assert gateway.diagnostics_calls == 1


def test_rust_quote_runtime_diagnostics_do_not_touch_live_gateway_directly() -> None:
    runtime = RustQuoteRuntime(_config=object())

    class _FailingGateway:
        def diagnostics(self) -> dict[str, object]:
            raise AssertionError("live gateway diagnostics must not be called")

        def diagnostics_handle(self) -> _FakeDiagnosticsHandle:
            return _FakeDiagnosticsHandle(_FakeGateway())

    runtime._gateway = _FailingGateway()
    runtime._gateway_diag_handle = runtime._gateway.diagnostics_handle()
    runtime._connected = True
    runtime._started = True

    diag = runtime.diagnostics()

    assert diag["raw_quote_event_count_1s"] == 9


class _ConcurrencyGuard:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.calls: list[list[str]] = []
        self._lock = threading.Lock()

    def call(self, symbols: list[str]) -> list[str]:
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            time.sleep(0.05)
            self.calls.append(list(symbols))
            return list(symbols)
        finally:
            with self._lock:
                self.active -= 1


@pytest.mark.asyncio
async def test_rust_quote_runtime_serializes_gateway_rest_calls() -> None:
    runtime = RustQuoteRuntime(_config=object())
    gateway = _ConcurrencyGuard()
    runtime._gateway = gateway

    results: list[list[str]] = []

    def _run(symbols: list[str]) -> None:
        results.append(runtime._call_gateway_serialized(lambda owned_gateway: owned_gateway.call(symbols), gateway))

    first = threading.Thread(target=_run, args=(["SPY.US"],))
    second = threading.Thread(target=_run, args=([".VIX.US"],))
    first.start()
    second.start()
    first.join(timeout=1.0)
    second.join(timeout=1.0)

    assert first.is_alive() is False
    assert second.is_alive() is False
    assert sorted(results) == [[".VIX.US"], ["SPY.US"]]
    assert gateway.calls == [["SPY.US"], [".VIX.US"]]
    assert gateway.max_active == 1
