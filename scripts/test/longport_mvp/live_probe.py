from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime
from typing import Callable

from longport.openapi import Config, QuoteContext

from .constants import (
    DEFAULT_CONFIG,
    ET,
    ProbeConfig,
    QUADRANT_CALL_ASK,
    QUADRANT_CALL_BID,
    QUADRANT_PUT_ASK,
    QUADRANT_PUT_BID,
)
from .extractors import (
    classify_trade_side,
    exposure_delta_gamma,
    extract_trade_price,
    extract_trade_direction,
    extract_trade_session,
    extract_trade_type,
    extract_trade_volume,
    is_trade_condition_filtered,
    oi_participation,
    parse_option_type,
    quadrant_for,
    tick_rule_direction,
)
from .flow import FlowTick, FlowWindow, SuppressionStateMachine, UnderlyingTape
from .models import LiveSample, LiveStats, contract_identity
from .stores import GreeksCache, OICache, RecentTradeStore, TopOfBookCache


def first_env(*names: str) -> str:
    for name in names:
        value = str(os.getenv(name, "")).strip()
        if value:
            return value
    return ""


def build_quote_context() -> QuoteContext:
    app_key = first_env("LONGPORT_APP_KEY", "LONGBRIDGE_APP_KEY")
    app_secret = first_env("LONGPORT_APP_SECRET", "LONGBRIDGE_APP_SECRET")
    access_token = first_env("LONGPORT_ACCESS_TOKEN", "LONGBRIDGE_ACCESS_TOKEN")
    http_url = first_env("LONGPORT_HTTP_URL", "LONGBRIDGE_HTTP_URL") or None
    quote_ws_url = first_env("LONGPORT_QUOTE_WS_URL", "LONGBRIDGE_QUOTE_WS_URL") or None
    trade_ws_url = first_env("LONGPORT_TRADE_WS_URL", "LONGBRIDGE_TRADE_WS_URL") or None
    return QuoteContext(
        Config(
            app_key,
            app_secret,
            access_token,
            http_url=http_url,
            quote_ws_url=quote_ws_url,
            trade_ws_url=trade_ws_url,
        )
    )


async def run_live_probe(
    config: ProbeConfig = DEFAULT_CONFIG,
    sample_hook: Callable[[LiveSample], None] | None = None,
) -> LiveStats:
    from shared.services.l0_runtime.services.runtime.builder import OptionChainBuilder

    tobs = TopOfBookCache()
    oi_cache = OICache()
    greeks_cache = GreeksCache()
    recent_large_trades = RecentTradeStore(maxlen=50_000, ttl_sec=900.0)
    seen_cluster_keys: set[str] = set()
    last_trade_direction: dict[str, int] = {}
    last_trade_price: dict[str, float] = {}
    flow_window = FlowWindow(
        window_sec=config.rolling_window_sec,
        z_threshold=config.z_threshold,
        min_oi_participation=config.min_oi_participation,
    )
    suppression = SuppressionStateMachine(dom_threshold=config.dom_threshold, hold_sec=config.hold_sec)
    underlying_tape = UnderlyingTape(window_sec=config.rolling_window_sec)
    stats = LiveStats()
    seen_option_symbols: set[str] = set()
    builder = OptionChainBuilder()
    quote_ctx = build_quote_context()
    stop_underlying = asyncio.Event()
    underlying_task: asyncio.Task | None = None
    start_mono = time.monotonic()

    def _build_sample(elapsed_sec: float) -> LiveSample:
        return LiveSample(
            timestamp_et=datetime.now(ET).isoformat(),
            elapsed_sec=elapsed_sec,
            depth_events=stats.depth_events,
            trade_events=stats.trade_events,
            classified_total=stats.classified_total,
            oi_enriched_events=stats.oi_enriched_events,
            oi_enriched_ratio=stats.oi_enriched_ratio,
            oi_symbols_cached=stats.oi_symbols_cached,
            large_flow_hits=stats.large_flow_hits,
            suppression_state=stats.suppression_state,
            dominance_latest=stats.dominance_latest,
            underlying_tape_samples=stats.underlying_tape_samples,
            fetch_snapshot_calls=stats.fetch_snapshot_calls,
            option_quote_calls=stats.option_quote_calls,
            underlying_pull_calls=stats.underlying_pull_calls,
            net_delta_exposure_live=stats.net_delta_exposure_live,
            net_gamma_exposure_live=stats.net_gamma_exposure_live,
            midpoint_tickrule_count=stats.midpoint_tickrule_count,
            condition_filtered_count=stats.condition_filtered_count,
            complex_spread_count=stats.complex_spread_count,
            residual_delta_after_netting=stats.residual_delta_after_netting,
            greek_stale_reads=stats.greek_stale_reads,
            put_ask_hits=stats.quadrant_hits.get(QUADRANT_PUT_ASK, 0),
            call_bid_hits=stats.quadrant_hits.get(QUADRANT_CALL_BID, 0),
            put_bid_hits=stats.quadrant_hits.get(QUADRANT_PUT_BID, 0),
            call_ask_hits=stats.quadrant_hits.get(QUADRANT_CALL_ASK, 0),
        )

    def on_depth(symbol: str, bids: list[object], asks: list[object]) -> None:
        tobs.update(symbol, bids, asks)
        stats.depth_events += 1

    def on_trade(symbol: str, trades: list[dict[str, object]]) -> None:
        stats.trade_events += len(trades)
        option_type = parse_option_type(symbol)
        if option_type is None:
            return
        seen_option_symbols.add(symbol)
        bid1, ask1 = tobs.get(symbol)
        for trade in trades:
            if is_trade_condition_filtered(trade):
                stats.condition_filtered_count += 1
                continue
            side = classify_trade_side(price=extract_trade_price(trade), bid1=bid1, ask1=ask1)
            stats.classified_total += 1
            quadrant = quadrant_for(option_type, side)
            if quadrant is None:
                continue
            stats.quadrant_hits[quadrant] += 1

            oi = oi_cache.get(symbol)
            price = extract_trade_price(trade)
            volume = extract_trade_volume(trade)
            if oi is None or oi <= 0 or price is None or volume is None:
                continue
            direction = extract_trade_direction(trade)
            if direction == 0:
                direction = tick_rule_direction(
                    price=price,
                    bid1=bid1,
                    ask1=ask1,
                    prev_price=last_trade_price.get(symbol),
                    prev_direction=last_trade_direction.get(symbol, 0),
                )
                stats.midpoint_tickrule_count += 1
            if direction != 0:
                last_trade_direction[symbol] = direction
            last_trade_price[symbol] = price
            delta, gamma, stale = greeks_cache.get(symbol, now_mono=time.monotonic(), max_age_sec=120.0)
            if stale:
                stats.greek_stale_reads += 1
            delta_exp, gamma_exp = exposure_delta_gamma(direction=direction, size=volume, delta=delta, gamma=gamma)
            stats.oi_enriched_events += 1
            oi_part = oi_participation(volume, oi)
            score = abs(delta_exp)
            residual_delta = delta_exp
            if oi_part >= config.min_oi_participation:
                expiry, strike = contract_identity(symbol)
                recent_large_trades.add(
                    {
                        "timestamp_mono": time.monotonic(),
                        "expiry": expiry,
                        "strike": strike,
                        "delta_exposure": delta_exp,
                        "option_type": option_type,
                        "trade_type": extract_trade_type(trade) or "UNKNOWN",
                        "trade_session": extract_trade_session(trade) or "UNKNOWN",
                    },
                    now_mono=time.monotonic(),
                )
                cluster_rows = recent_large_trades.cluster_window(now_mono=time.monotonic(), window_sec=0.05)
                legs = {(str(row.get("expiry", "")), str(row.get("strike", "")), str(row.get("option_type", ""))) for row in cluster_rows}
                if len(cluster_rows) >= 2 and len(legs) >= 2:
                    cluster_key = f"{int(time.monotonic() * 20)}:{sorted(legs)}"
                    residual_delta = float(sum(float(row.get("delta_exposure", 0.0) or 0.0) for row in cluster_rows))
                    score = abs(residual_delta)
                    if cluster_key not in seen_cluster_keys:
                        seen_cluster_keys.add(cluster_key)
                        stats.complex_spread_count += 1
                    else:
                        residual_delta = 0.0
                        score = 0.0
            is_large = flow_window.add(
                FlowTick(
                    timestamp_mono=time.monotonic(),
                    quadrant=quadrant,
                    score=score,
                    oi_participation=oi_part,
                    delta_exposure=residual_delta,
                    gamma_exposure=gamma_exp,
                    residual_delta=residual_delta,
                )
            )
            stats.last_zscore = flow_window.last_zscore
            if is_large:
                stats.large_flow_hits += 1
                stats.large_hits_by_quadrant[quadrant] += 1

    async def pull_underlying_realtime_trades() -> None:
        while not stop_underlying.is_set():
            try:
                stats.underlying_pull_calls += 1
                rows = await asyncio.to_thread(quote_ctx.realtime_trades, "SPY.US", config.underlying_pull_count)
                if asyncio.iscoroutine(rows):
                    rows = await rows
                underlying_tape.update(rows, now_mono=time.monotonic())
                stats.underlying_tape_samples = underlying_tape.samples
            except Exception:
                stats.underlying_pull_failures += 1
            await asyncio.sleep(config.underlying_pull_interval_sec)

    builder.on_depth = on_depth
    builder.on_trade = on_trade
    stats.start_et = datetime.now(ET).isoformat()
    stats.end_et = stats.start_et

    try:
        await builder.initialize()
        now_mono = time.monotonic()
        stats.fetch_snapshot_calls += 1
        snapshot = await builder.fetch_snapshot()
        oi_cache.bulk_update_snapshot(snapshot.get("chain"), now_mono=now_mono)
        greeks_cache.bulk_update_snapshot(snapshot.get("chain"), now_mono=now_mono)
        stats.oi_symbols_cached = oi_cache.size
        underlying_task = asyncio.create_task(pull_underlying_realtime_trades())

        deadline = time.monotonic() + config.timeout_sec
        next_oi_refresh = 0.0
        next_sample = 0.0
        while time.monotonic() < deadline:
            now_mono = time.monotonic()
            if now_mono >= next_oi_refresh:
                stats.fetch_snapshot_calls += 1
                snapshot = await builder.fetch_snapshot()
                oi_cache.bulk_update_snapshot(snapshot.get("chain"), now_mono=now_mono)
                greeks_cache.bulk_update_snapshot(snapshot.get("chain"), now_mono=now_mono)
                stats.oi_symbols_cached = oi_cache.size
                missing = oi_cache.missing_symbols(
                    seen_option_symbols,
                    now_mono=now_mono,
                    max_age_sec=config.oi_max_age_sec,
                )
                if missing:
                    try:
                        runtime = builder._runtime_bundle.quote_runtime
                        stats.option_quote_calls += 1
                        rows = await runtime.option_quote(sorted(missing)[: config.oi_backfill_batch_size])
                        if oi_cache.bulk_update_quote_rows(rows, now_mono=now_mono) > 0:
                            stats.oi_backfill_batches += 1
                        greeks_cache.bulk_update_quote_rows(rows, now_mono=now_mono)
                    except Exception:
                        stats.oi_backfill_failures += 1
                next_oi_refresh = now_mono + config.oi_refresh_sec

            bear_score = flow_window.window_sum(QUADRANT_PUT_ASK, now_mono) + flow_window.window_sum(QUADRANT_CALL_BID, now_mono)
            bull_score = flow_window.window_sum(QUADRANT_CALL_ASK, now_mono) + flow_window.window_sum(QUADRANT_PUT_BID, now_mono)
            suppression.update(
                now_mono=now_mono,
                bear_score=bear_score,
                bull_score=bull_score,
                underlying_bias=underlying_tape.direction_bias(now_mono),
                micro_ret=underlying_tape.micro_return(now_mono),
            )
            stats.suppression_state = suppression.state
            stats.dominance_latest = suppression.dominance
            stats.net_delta_exposure_live = flow_window.window_net_delta(now_mono)
            stats.net_gamma_exposure_live = flow_window.window_net_gamma(now_mono)
            stats.residual_delta_after_netting = flow_window.window_residual_delta(now_mono)
            if sample_hook is not None and now_mono >= next_sample:
                sample_hook(_build_sample(elapsed_sec=max(0.0, now_mono - start_mono)))
                next_sample = now_mono + config.sample_interval_sec
            await asyncio.sleep(0.25)
        stats.end_et = datetime.now(ET).isoformat()
    finally:
        stop_underlying.set()
        if underlying_task is not None:
            await asyncio.gather(underlying_task, return_exceptions=True)
        if hasattr(quote_ctx, "close"):
            await asyncio.to_thread(quote_ctx.close)
        try:
            await builder.shutdown()
        except RuntimeError:
            # Some native reader states can throw "Already borrowed" during shutdown.
            # Monitoring artifact is already captured; keep probe completion resilient.
            pass

    if sample_hook is not None:
        sample_hook(_build_sample(elapsed_sec=max(0.0, time.monotonic() - start_mono)))

    return stats
