from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from shared.services.l0_runtime.services.orchestration.orchestrator import FeedOrchestrator


class _StubStore:
    def __init__(self) -> None:
        self.spot = 100.0
        self._last_spot_update = datetime.now(ZoneInfo("US/Eastern"))
        self.volume_map: dict[float, int] = {}

    def update_volume_map(self, volume_map: dict[float, int]) -> None:
        self.volume_map = dict(volume_map)


class _StubSubMgr:
    def __init__(self) -> None:
        self.subscribed_symbols: set[str] = set()
        self.refresh_calls = 0
        self.last_mandatory_symbols: set[str] | None = None

    async def refresh(self, spot: float | None, mandatory_symbols: set[str] | None = None) -> set[str]:
        del spot
        self.last_mandatory_symbols = set(mandatory_symbols or set())
        self.refresh_calls += 1
        if self.refresh_calls == 1:
            self.subscribed_symbols = {"A", "B"}
        elif self.refresh_calls == 2:
            self.subscribed_symbols = {"A", "B", "C"}
        return set(self.subscribed_symbols)


class _StubIVSync:
    def __init__(self) -> None:
        self.bootstrap_warmup_done = False
        self.warming_up = False
        self.calls: list[set[str]] = []

    async def warm_up(self, symbols: list[str]) -> None:
        self.calls.append(set(symbols))


class _StubLimiter:
    cooldown_active = False
    max_symbol_weight = 50

    def maybe_promote_to_steady(self, **kwargs) -> bool:
        del kwargs
        return False

    def cooldown_stable_for(self, seconds: float) -> bool:
        del seconds
        return True

    class _AcquireCtx:
        async def __aenter__(self) -> None:
            return None

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            del exc_type, exc, tb
            return False

    def acquire(self, weight: int = 1) -> "_StubLimiter._AcquireCtx":
        del weight
        return self._AcquireCtx()


class _StubQuoteRuntime:
    def __init__(self, *, hv_values: list[float | None]) -> None:
        self._hv_values = hv_values
        self.option_chain_info_calls = 0
        self.option_quote_calls = 0

    async def option_chain_info_by_date(self, symbol: str, expiry) -> list[SimpleNamespace]:
        del symbol, expiry
        self.option_chain_info_calls += 1
        return [
            SimpleNamespace(price=560.0, call_symbol="SPY_C560", put_symbol="SPY_P560"),
        ]

    async def option_quote(self, symbols: list[str]) -> list[SimpleNamespace]:
        self.option_quote_calls += 1
        rows: list[SimpleNamespace] = []
        for idx, symbol in enumerate(symbols):
            hv = self._hv_values[idx] if idx < len(self._hv_values) else None
            rows.append(
                SimpleNamespace(
                    symbol=symbol,
                    volume=100 if "C" in symbol else 80,
                    historical_volatility_decimal=hv,
                    historical_volatility=None,
                )
            )
        return rows


class _RepairRuntimeStub:
    def __init__(self) -> None:
        self.option_quote_calls: list[list[str]] = []

    async def option_quote(self, symbols: list[str]) -> list[SimpleNamespace]:
        self.option_quote_calls.append(list(symbols))
        return [SimpleNamespace(symbol=symbol, last_done=2.45) for symbol in symbols]


@pytest.mark.asyncio
async def test_orchestrator_throttles_refresh_and_merges_warmup_symbols() -> None:
    store = _StubStore()
    sub_mgr = _StubSubMgr()
    iv_sync = _StubIVSync()
    limiter = _StubLimiter()
    orchestrator = FeedOrchestrator(
        quote_runtime=object(),  # not used in this test
        store=store,
        sub_mgr=sub_mgr,
        iv_sync=iv_sync,
        rate_limiter=limiter,
    )

    async def _pass_spot(spot: float | None, now: datetime) -> float | None:
        del now
        return spot

    orchestrator._refresh_spot_if_needed = _pass_spot  # type: ignore[assignment]

    class _Clock:
        now = 100.0

    clock = _Clock()
    orchestrator._monotonic = lambda: clock.now

    await orchestrator._tick()  # refresh #1 -> queue A/B
    clock.now = 105.0
    await orchestrator._tick()  # no refresh
    clock.now = 121.0
    await orchestrator._tick()  # flush A/B after 20s merge window
    clock.now = 131.0
    await orchestrator._tick()  # refresh #2 -> queue C
    clock.now = 152.0
    await orchestrator._tick()  # flush C

    assert sub_mgr.refresh_calls == 2
    assert iv_sync.calls == [{"A", "B"}, {"C"}]


@pytest.mark.asyncio
async def test_volume_research_updates_official_hv_diagnostics_without_extra_calls() -> None:
    store = _StubStore()
    sub_mgr = _StubSubMgr()
    iv_sync = _StubIVSync()
    limiter = _StubLimiter()
    runtime = _StubQuoteRuntime(hv_values=[0.18, 0.20])
    orchestrator = FeedOrchestrator(
        quote_runtime=runtime,
        store=store,
        sub_mgr=sub_mgr,
        iv_sync=iv_sync,
        rate_limiter=limiter,
    )

    await orchestrator._run_volume_research("20260312", 560.0)

    diag = orchestrator.official_hv_diagnostics
    assert runtime.option_chain_info_calls == 1
    assert runtime.option_quote_calls == 1
    assert store.volume_map == {560.0: 180}
    assert diag["official_hv_decimal"] == pytest.approx(0.19)
    assert diag["official_hv_sample_count"] == 2
    assert isinstance(diag["official_hv_synced_at_utc"], str)


@pytest.mark.asyncio
async def test_volume_research_keeps_official_hv_none_when_samples_missing() -> None:
    store = _StubStore()
    sub_mgr = _StubSubMgr()
    iv_sync = _StubIVSync()
    limiter = _StubLimiter()
    runtime = _StubQuoteRuntime(hv_values=[None, None])
    orchestrator = FeedOrchestrator(
        quote_runtime=runtime,
        store=store,
        sub_mgr=sub_mgr,
        iv_sync=iv_sync,
        rate_limiter=limiter,
    )

    await orchestrator._run_volume_research("20260312", 560.0)

    diag = orchestrator.official_hv_diagnostics
    assert diag["official_hv_decimal"] is None
    assert diag["official_hv_sample_count"] == 0
    assert diag["official_hv_synced_at_utc"] is None


@pytest.mark.asyncio
async def test_orchestrator_repairs_mandatory_anchor_prices_without_waiting_for_iv_cycle() -> None:
    store = _StubStore()
    sub_mgr = _StubSubMgr()
    iv_sync = _StubIVSync()
    limiter = _StubLimiter()
    runtime = _RepairRuntimeStub()
    repaired: list[tuple[str, float | None]] = []
    orchestrator = FeedOrchestrator(
        quote_runtime=runtime,
        store=store,
        sub_mgr=sub_mgr,
        iv_sync=iv_sync,
        rate_limiter=limiter,
        on_price_repair_update=lambda symbol, item: repaired.append((symbol, getattr(item, "last_done", None))),
        needs_price_repair_fn=lambda symbol: symbol == "SPY260324C652000.US",
    )

    async def _pass_spot(spot: float | None, now: datetime) -> float | None:
        del now
        return spot

    orchestrator._refresh_spot_if_needed = _pass_spot  # type: ignore[assignment]
    orchestrator.set_mandatory_symbols({"SPY260324C652000.US"})
    orchestrator._last_refresh_mono = 100.0
    orchestrator._monotonic = lambda: 105.0

    await orchestrator._tick()

    assert runtime.option_quote_calls == [["SPY260324C652000.US"]]
    assert repaired == [("SPY260324C652000.US", 2.45)]


@pytest.mark.asyncio
async def test_repair_symbols_once_repairs_explicit_startup_anchor_batch() -> None:
    store = _StubStore()
    sub_mgr = _StubSubMgr()
    iv_sync = _StubIVSync()
    limiter = _StubLimiter()
    runtime = _RepairRuntimeStub()
    repaired: list[str] = []
    orchestrator = FeedOrchestrator(
        quote_runtime=runtime,
        store=store,
        sub_mgr=sub_mgr,
        iv_sync=iv_sync,
        rate_limiter=limiter,
        on_price_repair_update=lambda symbol, item: repaired.append(symbol),
        needs_price_repair_fn=lambda symbol: True,
    )

    updated = await orchestrator.repair_symbols_once(
        {"SPY260324C659000.US", "SPY260324P659000.US"},
        now_mono=123.0,
        log_prefix="[Test]",
    )

    assert updated == 2
    assert runtime.option_quote_calls == [["SPY260324C659000.US", "SPY260324P659000.US"]]
    assert repaired == ["SPY260324C659000.US", "SPY260324P659000.US"]


@pytest.mark.asyncio
async def test_refresh_subscriptions_once_uses_current_mandatory_symbols() -> None:
    store = _StubStore()
    sub_mgr = _StubSubMgr()
    iv_sync = _StubIVSync()
    limiter = _StubLimiter()
    orchestrator = FeedOrchestrator(
        quote_runtime=object(),
        store=store,
        sub_mgr=sub_mgr,
        iv_sync=iv_sync,
        rate_limiter=limiter,
    )

    orchestrator.set_mandatory_symbols({"SPY260324C660000.US", "SPY260324P660000.US"})
    target = await sub_mgr.refresh(store.spot, mandatory_symbols=orchestrator.mandatory_symbols)

    assert sub_mgr.last_mandatory_symbols == {"SPY260324C660000.US", "SPY260324P660000.US"}
    assert target

