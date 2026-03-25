from __future__ import annotations

from types import SimpleNamespace

import pytest

from shared.services.l0_runtime.services.sync.iv_baseline_sync import IVBaselineSync


class _LimiterStub:
    max_symbol_weight = 50

    class _AcquireCtx:
        async def __aenter__(self) -> None:
            return None

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            del exc_type, exc, tb
            return False

    def acquire(self, weight: int = 1) -> "_LimiterStub._AcquireCtx":
        del weight
        return self._AcquireCtx()

    def trigger_cooldown(self, seconds: int | None = None) -> None:
        del seconds


class _RuntimeStub:
    def __init__(self) -> None:
        self.calc_indexes_calls: list[list[str]] = []
        self.option_quote_calls: list[list[str]] = []

    async def calc_indexes(self, symbols: list[str], indexes: list[object]) -> list[SimpleNamespace]:
        del indexes
        self.calc_indexes_calls.append(list(symbols))
        return [
            SimpleNamespace(
                symbol=symbol,
                implied_volatility=19.5,
                open_interest=1200,
                last_done=None,
                volume=None,
                turnover=None,
            )
            for symbol in symbols
        ]

    async def option_quote(self, symbols: list[str]) -> list[SimpleNamespace]:
        self.option_quote_calls.append(list(symbols))
        return [
            SimpleNamespace(
                symbol=symbol,
                last_done=2.45,
                volume=100,
                turnover=2500.0,
                open_interest=1200,
                implied_volatility=0.19,
            )
            for symbol in symbols
        ]


@pytest.mark.asyncio
async def test_sync_batches_repairs_anchor_prices_via_option_quote() -> None:
    runtime = _RuntimeStub()
    sync = IVBaselineSync(_LimiterStub())
    updates: list[tuple[str, float | None]] = []
    repaired = {"SPY260324C652000.US"}

    sync.start(
        runtime,
        get_symbols_fn=lambda: set(repaired),
        get_spot_fn=lambda: 652.0,
        on_update=lambda symbol, item: updates.append((symbol, getattr(item, "last_done", None))),
        get_price_repair_symbols_fn=lambda: set(repaired),
        needs_price_repair_fn=lambda symbol: symbol in repaired,
    )

    await sync._sync_batches(
        symbols=["SPY260324C652000.US"],
        spot_provider=lambda: 652.0,
        warm_up_mode=False,
    )

    assert runtime.calc_indexes_calls == [["SPY260324C652000.US"]]
    assert runtime.option_quote_calls == [["SPY260324C652000.US"]]
    assert updates == [
        ("SPY260324C652000.US", None),
        ("SPY260324C652000.US", 2.45),
    ]


@pytest.mark.asyncio
async def test_sync_batches_skips_price_repair_for_non_anchor_symbols() -> None:
    runtime = _RuntimeStub()
    sync = IVBaselineSync(_LimiterStub())

    sync.start(
        runtime,
        get_symbols_fn=lambda: {"SPY260324C652000.US"},
        get_spot_fn=lambda: 652.0,
        on_update=lambda symbol, item: None,
        get_price_repair_symbols_fn=lambda: {"SPY260324P652000.US"},
        needs_price_repair_fn=lambda symbol: True,
    )

    await sync._sync_batches(
        symbols=["SPY260324C652000.US"],
        spot_provider=lambda: 652.0,
        warm_up_mode=False,
    )

    assert runtime.calc_indexes_calls == [["SPY260324C652000.US"]]
    assert runtime.option_quote_calls == []

