from __future__ import annotations

import json
import os
from datetime import date
from types import SimpleNamespace

import pytest
from longport.openapi import CalcIndex

from l0_ingest.feeds.quote_runtime import PythonQuoteRuntime, RustQuoteRuntime


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
                    "prev_close": 1.0,
                    "open": 1.1,
                    "high": 1.3,
                    "low": 0.9,
                    "timestamp": 1700000000,
                    "volume": 3,
                    "turnover": 120.5,
                    "trade_status": 0,
                    "option_extend": {
                        "implied_volatility": "0.25",
                        "open_interest": 4,
                        "expiry_date": "20260101",
                        "strike_price": "560",
                        "contract_multiplier": "100",
                        "contract_type": "A",
                        "contract_size": "100",
                        "direction": "C",
                        "historical_volatility": "0.21",
                        "underlying_symbol": "SPY.US",
                    },
                    "open_interest": 4,
                    "implied_volatility": 0.25,
                    "implied_volatility_raw": "0.25",
                    "expiry_date": "20260101",
                    "expiry_date_raw": "20260101",
                    "strike_price": 560.0,
                    "strike_price_raw": "560",
                    "contract_multiplier": 100.0,
                    "contract_type": "A",
                    "contract_size": 100.0,
                    "direction": "C",
                    "historical_volatility": 0.21,
                    "historical_volatility_raw": "0.21",
                    "underlying_symbol": "SPY.US",
                }
            ]
        )

    def rest_option_chain_info_by_date(self, _symbol: str, _expiry: str) -> str:
        return json.dumps(
            [
                {
                    "price": 560.0,
                    "price_raw": "560",
                    "strike_price": 560.0,
                    "call_symbol": "C560",
                    "put_symbol": "P560",
                    "standard": True,
                }
            ]
        )

    def rest_calc_indexes(self, _symbols: list[str], indexes: list[str]) -> str:
        self.last_indexes = list(indexes)
        return json.dumps(
            [
                {
                    "symbol": "OPT1",
                    "last_done": 1.2,
                    "change_val": 0.1,
                    "change_rate": 0.05,
                    "volume": 10,
                    "turnover": 20.5,
                    "expiry_date": "20260101",
                    "expiry_date_raw": "20260101",
                    "strike_price": 560.0,
                    "strike_price_raw": "560",
                    "premium": 0.12,
                    "open_interest": 20,
                    "implied_volatility": 0.22,
                    "implied_volatility_raw": "0.22",
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


class _FakeQuoteContext:
    def quote(self, symbols: list[str]) -> list[SimpleNamespace]:
        return [SimpleNamespace(symbol=symbols[0], last_done=100.5, volume=12, turnover=2.2, timestamp=1)]

    def option_quote(self, symbols: list[str]) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                symbol=symbols[0],
                last_done=1.2,
                prev_close=1.0,
                open=1.1,
                high=1.3,
                low=0.9,
                timestamp=1700000000,
                volume=3,
                turnover=120.5,
                trade_status=SimpleNamespace(value=0),
                implied_volatility=0.25,
                open_interest=4,
                expiry_date="20260101",
                strike_price=560.0,
                contract_multiplier=100.0,
                contract_type="A",
                contract_size=100.0,
                direction="C",
                historical_volatility=0.21,
                underlying_symbol="SPY.US",
            )
        ]

    def option_chain_info_by_date(self, _symbol: str, _expiry: date) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                price=560.0,
                call_symbol="C560",
                put_symbol="P560",
                standard=True,
            )
        ]

    def calc_indexes(self, _symbols: list[str], _indexes: list[CalcIndex]) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                symbol="OPT1",
                last_done=1.2,
                change_val=0.1,
                change_rate=0.05,
                volume=10,
                turnover=20.5,
                expiry_date="20260101",
                strike_price=560.0,
                premium=0.12,
                implied_volatility=0.22,
                open_interest=20,
                delta=0.5,
                gamma=0.1,
                theta=-0.02,
                vega=0.03,
                rho=0.01,
            )
        ]


class _FakeMarketDataGateway:
    def __init__(self, config: object, primary_ctx: object | None) -> None:
        del config, primary_ctx
        self.quote_ctx = _FakeQuoteContext()
        self.event_queue = None

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    def subscribe(self, symbols: list[str], sub_types: list[object]) -> None:
        del symbols, sub_types

    def diagnostics(self) -> dict[str, object]:
        return {"connected": True}


class _FailoverGateway:
    def __init__(self, fail_connect: bool) -> None:
        self.fail_connect = fail_connect

    def rest_quote(self, symbols: list[str]) -> str:
        if self.fail_connect:
            raise RuntimeError(
                "QuoteContext init failed: error sending request for url "
                "(https://openapi.longportapp.com/v2/socket/token): client error (Connect)"
            )
        return json.dumps(
            [{"symbol": symbols[0], "last_done": 100.5, "volume": 12, "turnover": 2.2, "timestamp": 1}]
        )


@pytest.mark.asyncio
async def test_rust_quote_runtime_decodes_rows_and_indexes(monkeypatch):
    fake = _FakeRustGateway()
    monkeypatch.setattr(
        "l0_ingest.feeds.quote_runtime.l0_rust",
        SimpleNamespace(RustIngestGateway=lambda: fake),
    )

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
    assert option_quotes[0].option_extend is not None
    assert option_quotes[0].option_extend.underlying_symbol == "SPY.US"
    assert option_quotes[0].expiry_date == "2026-01-01"
    assert option_quotes[0].implied_volatility_decimal == pytest.approx(0.25)
    assert chain_info[0].call_symbol == "C560"
    assert chain_info[0].standard is True
    assert chain_info[0].strike_price == pytest.approx(560.0)
    assert calc[0].implied_volatility == 0.22
    assert calc[0].change_val == pytest.approx(0.1)
    assert calc[0].turnover == pytest.approx(20.5)
    assert calc[0].expiry_date == "2026-01-01"
    assert calc[0].premium == pytest.approx(0.12)
    assert fake.last_indexes == ["ImpliedVolatility", "OpenInterest", "Volume"]


@pytest.mark.asyncio
async def test_rust_quote_runtime_disconnect_stops_gateway(monkeypatch):
    fake = _FakeRustGateway()
    monkeypatch.setattr(
        "l0_ingest.feeds.quote_runtime.l0_rust",
        SimpleNamespace(RustIngestGateway=lambda: fake),
    )

    runtime = RustQuoteRuntime(_DummyConfig())
    await runtime.connect()
    await runtime.subscribe(["SPY.US"])
    await runtime.disconnect()

    assert fake.stopped is True


@pytest.mark.asyncio
async def test_rust_quote_runtime_switches_endpoint_profile_on_connectivity_failure(monkeypatch):
    snapshots: list[tuple[str | None, str | None, str | None]] = []
    instances: list[_FailoverGateway] = []

    def _factory() -> _FailoverGateway:
        gateway = _FailoverGateway(fail_connect=(len(instances) == 0))
        instances.append(gateway)
        snapshots.append(
            (
                os.environ.get("LONGPORT_HTTP_URL"),
                os.environ.get("LONGPORT_QUOTE_WS_URL"),
                os.environ.get("LONGPORT_TRADE_WS_URL"),
            )
        )
        return gateway

    monkeypatch.setattr(
        "l0_ingest.feeds.quote_runtime.l0_rust",
        SimpleNamespace(RustIngestGateway=_factory),
    )
    runtime = RustQuoteRuntime(
        _DummyConfig(),
        endpoint_profiles=[
            {
                "name": "primary",
                "http_url": "https://openapi.longportapp.com",
                "quote_ws_url": "wss://openapi-quote.longportapp.com/v2",
                "trade_ws_url": "wss://openapi-trade.longportapp.com/v2",
            },
            {
                "name": "official_longbridge",
                "http_url": "https://openapi.longbridge.com",
                "quote_ws_url": "wss://openapi-quote.longbridge.com/v2",
                "trade_ws_url": "wss://openapi-trade.longbridge.com/v2",
            },
        ],
    )

    quotes = await runtime.quote(["SPY.US"])

    assert quotes[0].symbol == "SPY.US"
    assert len(instances) == 2
    assert snapshots[0] == (
        "https://openapi.longportapp.com",
        "wss://openapi-quote.longportapp.com/v2",
        "wss://openapi-trade.longportapp.com/v2",
    )
    assert snapshots[1] == (
        "https://openapi.longbridge.com",
        "wss://openapi-quote.longbridge.com/v2",
        "wss://openapi-trade.longbridge.com/v2",
    )
    assert runtime.diagnostics()["endpoint_profile"] == "official_longbridge"


@pytest.mark.asyncio
async def test_python_quote_runtime_maps_sdk_objects_to_contracts(monkeypatch):
    monkeypatch.setattr(
        "l0_ingest.feeds.quote_runtime.MarketDataGateway",
        _FakeMarketDataGateway,
    )

    runtime = PythonQuoteRuntime(_DummyConfig())
    option_quotes = await runtime.option_quote(["SPY260101C560000.US"])
    chain_info = await runtime.option_chain_info_by_date("SPY.US", date(2026, 1, 1))
    calc = await runtime.calc_indexes(
        ["SPY260101C560000.US"],
        [CalcIndex.ImpliedVolatility, CalcIndex.OpenInterest, CalcIndex.Volume],
    )

    assert option_quotes[0].symbol == "SPY260101C560000.US"
    assert option_quotes[0].option_extend is not None
    assert option_quotes[0].option_extend.contract_type == "A"
    assert option_quotes[0].expiry_date_iso == "2026-01-01"
    assert option_quotes[0].contract_multiplier == pytest.approx(100.0)
    assert chain_info[0].standard is True
    assert calc[0].implied_volatility_decimal == pytest.approx(0.22)
    assert calc[0].strike_price == pytest.approx(560.0)
