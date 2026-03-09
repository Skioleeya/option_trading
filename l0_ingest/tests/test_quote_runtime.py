from __future__ import annotations

import json
import sys
from datetime import date
from types import SimpleNamespace

import pytest
from longport.openapi import CalcIndex

from l0_ingest.feeds.quote_runtime import RustQuoteRuntime


class _FakeRustGateway:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.last_indexes: list[str] = []

    def start(self, symbols: list[str], shm_path: str, cpu_id: int) -> None:
        assert symbols
        assert shm_path
        assert cpu_id >= 0
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def rest_quote(self, symbols: list[str]) -> str:
        return json.dumps(
            [{"symbol": symbols[0], "last_done": 100.5, "volume": 12, "turnover": 2.2, "timestamp": 1}]
        )

    def rest_option_quote(self, symbols: list[str]) -> str:
        return json.dumps(
            [
                {
                    "symbol": symbols[0],
                    "last_done": 1.2,
                    "volume": 3,
                    "open_interest": 4,
                    "implied_volatility": 0.25,
                }
            ]
        )

    def rest_option_chain_info_by_date(self, _symbol: str, _expiry: str) -> str:
        return json.dumps([{"price": 560.0, "call_symbol": "C560", "put_symbol": "P560"}])

    def rest_calc_indexes(self, _symbols: list[str], indexes: list[str]) -> str:
        self.last_indexes = list(indexes)
        return json.dumps(
            [
                {
                    "symbol": "OPT1",
                    "volume": 10,
                    "open_interest": 20,
                    "implied_volatility": 0.22,
                    "delta": 0.5,
                    "gamma": 0.1,
                    "theta": -0.02,
                    "vega": 0.03,
                    "rho": 0.01,
                }
            ]
        )


class _DummyConfig:
    pass


@pytest.mark.asyncio
async def test_rust_quote_runtime_decodes_rows_and_indexes(monkeypatch):
    fake = _FakeRustGateway()
    monkeypatch.setitem(sys.modules, "l0_rust", SimpleNamespace(RustIngestGateway=lambda: fake))

    runtime = RustQuoteRuntime(_DummyConfig())
    await runtime.connect()
    await runtime.subscribe(["SPY.US"])

    quotes = await runtime.quote(["SPY.US"])
    option_quotes = await runtime.option_quote(["SPY260101C560000.US"])
    chain_info = await runtime.option_chain_info_by_date("SPY.US", date(2026, 1, 1))
    calc = await runtime.calc_indexes(
        ["SPY260101C560000.US"],
        [CalcIndex.ImpliedVolatility, CalcIndex.OpenInterest, "Volume"],
    )

    assert fake.started is True
    assert quotes[0].symbol == "SPY.US"
    assert option_quotes[0].open_interest == 4
    assert chain_info[0].call_symbol == "C560"
    assert calc[0].implied_volatility == 0.22
    assert fake.last_indexes == ["ImpliedVolatility", "OpenInterest", "Volume"]


@pytest.mark.asyncio
async def test_rust_quote_runtime_disconnect_stops_gateway(monkeypatch):
    fake = _FakeRustGateway()
    monkeypatch.setitem(sys.modules, "l0_rust", SimpleNamespace(RustIngestGateway=lambda: fake))

    runtime = RustQuoteRuntime(_DummyConfig())
    await runtime.connect()
    await runtime.subscribe(["SPY.US"])
    await runtime.disconnect()

    assert fake.stopped is True
