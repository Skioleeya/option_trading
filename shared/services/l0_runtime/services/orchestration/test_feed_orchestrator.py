from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from types import MethodType, SimpleNamespace

import pytest

from shared.services.l0_runtime.services.orchestration.feed_orchestrator import FeedOrchestrator


class _Store:
    def __init__(self, *, spot: float, source_timestamp_utc: str, last_spot_update: datetime) -> None:
        self.spot = spot
        self._source_timestamp_utc = source_timestamp_utc
        self.last_spot_update = last_spot_update

    def diagnostics(self) -> dict[str, object]:
        return {"quote_lane": {"last_source_timestamp_utc": self._source_timestamp_utc}}


class _Limiter:
    symbol_tokens = 0
    cooldown_active = False
    symbol_profile = "steady"
    cooldown_hits_5m = 0
    max_symbol_weight = 50

    def maybe_promote_to_steady(self, **_: object) -> None:
        return None

    def cooldown_stable_for(self, _: float) -> bool:
        return True


class _SubMgr:
    metadata_cache_hit_rate = 1.0

    def __init__(self, *, writer_ready: bool = False) -> None:
        self.subscribed_symbols: set[str] = set()
        self.refresh_calls: list[float] = []
        self._writer_ready = writer_ready

    @property
    def writer_ready(self) -> bool:
        return self._writer_ready

    async def refresh(self, spot: float, mandatory_symbols: set[str]) -> set[str]:
        self.refresh_calls.append(spot)
        del mandatory_symbols
        self._writer_ready = True
        return {"SPY.US"}


@pytest.mark.asyncio
async def test_feed_orchestrator_uses_raw_source_freshness_not_last_spot_update(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    now = datetime.now(timezone.utc)
    store = _Store(
        spot=705.25,
        source_timestamp_utc=(now - timedelta(seconds=1)).isoformat(),
        last_spot_update=now - timedelta(seconds=60),
    )
    sub_mgr = _SubMgr()
    orchestrator = FeedOrchestrator(
        quote_runtime=SimpleNamespace(),
        store=store,
        sub_mgr=sub_mgr,
        iv_sync=SimpleNamespace(bootstrap_warmup_done=True, warming_up=False),
        rate_limiter=_Limiter(),
    )
    orchestrator._refresh_min_interval_sec = 0.0
    events: list[str] = []

    async def _record_header(self: FeedOrchestrator, **_: object) -> None:
        events.append("header")

    async def _record_research(self: FeedOrchestrator, today_str: str, spot: float) -> None:
        del today_str, spot
        events.append("research")

    async def _noop(self: FeedOrchestrator, now_mono: float) -> None:
        del self, now_mono

    async def _noop_flush(self: FeedOrchestrator, now_mono: float) -> None:
        del self, now_mono

    orchestrator._refresh_header_volatility_aux = MethodType(_record_header, orchestrator)
    orchestrator._run_volume_research = MethodType(_record_research, orchestrator)
    orchestrator._repair_mandatory_prices = MethodType(_noop, orchestrator)
    orchestrator._flush_warmup_if_due = MethodType(_noop_flush, orchestrator)

    await orchestrator._tick()

    assert events == ["header", "research"]
    assert sub_mgr.refresh_calls == [705.25]
    assert "source stale gate active" not in caplog.text


@pytest.mark.asyncio
async def test_feed_orchestrator_skips_stale_source_work_and_recovers(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    now = datetime.now(timezone.utc)
    store = _Store(
        spot=705.25,
        source_timestamp_utc=(now - timedelta(seconds=11)).isoformat(),
        last_spot_update=now,
    )
    runtime = SimpleNamespace(quote_calls=[])
    sub_mgr = _SubMgr()
    orchestrator = FeedOrchestrator(
        quote_runtime=runtime,
        store=store,
        sub_mgr=sub_mgr,
        iv_sync=SimpleNamespace(bootstrap_warmup_done=True, warming_up=False),
        rate_limiter=_Limiter(),
    )
    orchestrator._refresh_min_interval_sec = 0.0
    events: list[str] = []

    async def _record_header(self: FeedOrchestrator, **_: object) -> None:
        events.append("header")

    async def _record_research(self: FeedOrchestrator, today_str: str, spot: float) -> None:
        del today_str, spot
        events.append("research")

    async def _noop(self: FeedOrchestrator, now_mono: float) -> None:
        del self, now_mono

    async def _noop_flush(self: FeedOrchestrator, now_mono: float) -> None:
        del self, now_mono

    orchestrator._refresh_header_volatility_aux = MethodType(_record_header, orchestrator)
    orchestrator._run_volume_research = MethodType(_record_research, orchestrator)
    orchestrator._repair_mandatory_prices = MethodType(_noop, orchestrator)
    orchestrator._flush_warmup_if_due = MethodType(_noop_flush, orchestrator)

    await orchestrator._tick()

    assert events == []
    assert sub_mgr.refresh_calls == []
    assert runtime.quote_calls == []
    assert "source stale gate active" in caplog.text

    caplog.clear()
    orchestrator._last_research = None
    store._source_timestamp_utc = datetime.now(timezone.utc).isoformat()

    await orchestrator._tick()

    assert events == ["header", "research"]
    assert sub_mgr.refresh_calls == [705.25]
    assert "source stale gate cleared" in caplog.text


@pytest.mark.asyncio
async def test_feed_orchestrator_bootstrap_allows_initial_subscription_refresh_without_source_timestamp(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    now = datetime.now(timezone.utc)
    store = _Store(
        spot=705.25,
        source_timestamp_utc="",
        last_spot_update=now,
    )
    sub_mgr = _SubMgr(writer_ready=False)
    orchestrator = FeedOrchestrator(
        quote_runtime=SimpleNamespace(),
        store=store,
        sub_mgr=sub_mgr,
        iv_sync=SimpleNamespace(bootstrap_warmup_done=True, warming_up=False),
        rate_limiter=_Limiter(),
    )
    orchestrator._refresh_min_interval_sec = 0.0
    events: list[str] = []

    async def _record_header(self: FeedOrchestrator, **_: object) -> None:
        events.append("header")

    async def _record_research(self: FeedOrchestrator, today_str: str, spot: float) -> None:
        del today_str, spot
        events.append("research")

    async def _noop(self: FeedOrchestrator, now_mono: float) -> None:
        del self, now_mono

    async def _noop_flush(self: FeedOrchestrator, now_mono: float) -> None:
        del self, now_mono

    orchestrator._refresh_header_volatility_aux = MethodType(_record_header, orchestrator)
    orchestrator._run_volume_research = MethodType(_record_research, orchestrator)
    orchestrator._repair_mandatory_prices = MethodType(_noop, orchestrator)
    orchestrator._flush_warmup_if_due = MethodType(_noop_flush, orchestrator)

    await orchestrator._tick()

    assert sub_mgr.refresh_calls == [705.25]
    assert events == []
    assert "bootstrap refresh path active" in caplog.text
    assert "source stale gate active" not in caplog.text


@pytest.mark.asyncio
async def test_feed_orchestrator_missing_source_timestamp_still_stale_after_bootstrap(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    now = datetime.now(timezone.utc)
    store = _Store(
        spot=705.25,
        source_timestamp_utc="",
        last_spot_update=now,
    )
    sub_mgr = _SubMgr(writer_ready=True)
    orchestrator = FeedOrchestrator(
        quote_runtime=SimpleNamespace(),
        store=store,
        sub_mgr=sub_mgr,
        iv_sync=SimpleNamespace(bootstrap_warmup_done=True, warming_up=False),
        rate_limiter=_Limiter(),
    )
    orchestrator._refresh_min_interval_sec = 0.0

    async def _unexpected(*_: object, **__: object) -> None:
        raise AssertionError("unexpected work executed during stale fast-fail")

    orchestrator._refresh_header_volatility_aux = MethodType(_unexpected, orchestrator)
    orchestrator._run_volume_research = MethodType(_unexpected, orchestrator)
    orchestrator._repair_mandatory_prices = MethodType(_unexpected, orchestrator)
    orchestrator._flush_warmup_if_due = MethodType(_unexpected, orchestrator)

    await orchestrator._tick()

    assert sub_mgr.refresh_calls == []
    assert "source stale gate active" in caplog.text
