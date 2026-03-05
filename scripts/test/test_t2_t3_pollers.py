"""Test T2/T3 Poller LongBridge Connectivity.

验证 Tier2Poller 和 Tier3Poller 能否：
1. 连接长桥 QuoteContext
2. 发现正确的到期日（metadata）
3. 通过 calc_indexes 拉取 IV/OI 数据

⚠️  重要: 此脚本会直接调用长桥 REST API。
    如果后端 uvicorn 同时在运行，两边的请求会叠加，可能超过 10次/秒的限制。
    脚本启动时会自动检测后端是否在运行，如果在运行则拒绝启动。

运行方式 (必须先停止后端):
    cd e:\\US.market\\Option_v3
    python scripts/test_t2_t3_pollers.py
"""

import asyncio
import sys
import time
import os
import socket

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from longport.openapi import QuoteContext, Config, CalcIndex
from shared.config import settings
from l0_ingest.feeds.rate_limiter import APIRateLimiter
from l0_ingest.feeds.tier2_poller import Tier2Poller
from l0_ingest.feeds.tier3_poller import Tier3Poller


def make_ctx() -> QuoteContext:
    config = Config(
        app_key=settings.longport_app_key,
        app_secret=settings.longport_app_secret,
        access_token=settings.longport_access_token,
    )
    return QuoteContext(config)


async def test_t2(ctx: QuoteContext, limiter: APIRateLimiter) -> None:
    print("\n" + "=" * 55)
    print("  T2 POLLER TEST  (2DTE expiry)")
    print("=" * 55)

    spot_holder: list[float] = [560.0]  # fallback spot

    # Try to get live SPY spot first
    try:
        quotes = ctx.quote(["SPY.US"])
        if quotes:
            spot_holder[0] = float(quotes[0].last_done)
            print(f"✅ Live SPY spot : {spot_holder[0]:.2f}")
        else:
            print(f"⚠️  No quote for SPY.US, using fallback spot={spot_holder[0]}")
    except Exception as e:
        print(f"⚠️  Quote failed ({e}), using fallback spot={spot_holder[0]}")

    poller = Tier2Poller(limiter)
    poller._ctx = ctx
    poller._get_spot = lambda: spot_holder[0]

    print("\n[T2] Refreshing metadata (scanning expiry dates)...")
    t0 = time.monotonic()
    ok = await poller._refresh_metadata()
    elapsed = time.monotonic() - t0

    if not ok:
        print("❌ T2 metadata refresh FAILED — cannot find 2DTE expiry")
        return

    print(f"✅ 2DTE expiry   : {poller._meta_expiry}  ({elapsed:.1f}s for metadata scan)")
    print(f"✅ Symbols found : {len(poller._meta_sym_to_strike)} within ±30pt")

    if not poller._meta_sym_to_strike:
        print("⚠️  No symbols in window — market may be closed or spot far from strikes")
        return

    # Test one data fetch cycle
    print("\n[T2] Running one data fetch cycle...")
    t1 = time.monotonic()
    await poller._fetch(spot_holder[0])
    elapsed2 = time.monotonic() - t1

    if poller.cache:
        sample = poller.cache[:3]
        print(f"✅ Data received : {len(poller.cache)} contracts in {elapsed2:.1f}s")
        for row in sample:
            print(f"   {row['symbol']} | strike={row['strike']} | IV={row['implied_volatility']:.2f} | OI={row['open_interest']}")
    else:
        print(f"❌ No data in cache after fetch ({elapsed2:.1f}s)")


async def test_t3(ctx: QuoteContext, limiter: APIRateLimiter) -> None:
    print("\n" + "=" * 55)
    print("  T3 POLLER TEST  (Weekly expiry)")
    print("=" * 55)

    spot_holder: list[float] = [560.0]
    try:
        quotes = ctx.quote(["SPY.US"])
        if quotes:
            spot_holder[0] = float(quotes[0].last_done)
    except Exception:
        pass

    print(f"[T3] Using spot : {spot_holder[0]:.2f}")

    poller = Tier3Poller(limiter)
    poller._ctx = ctx
    poller._get_spot = lambda: spot_holder[0]

    print("\n[T3] Refreshing metadata (scanning Weekly expiry)...")
    t0 = time.monotonic()
    ok = await poller._refresh_metadata()
    elapsed = time.monotonic() - t0

    if not ok:
        print("❌ T3 metadata refresh FAILED — cannot find Weekly expiry (Friday)")
        return

    print(f"✅ Weekly expiry : {poller._meta_expiry}  ({elapsed:.1f}s for metadata scan)")
    print(f"✅ Symbols found : {len(poller._meta_sym_to_strike)} within ±60pt")

    if not poller._meta_sym_to_strike:
        print("⚠️  No symbols in window — market may be closed or spot far from strikes")
        return

    # Test one data fetch cycle
    print("\n[T3] Running one data fetch cycle (Top 20 OI anchors)...")
    t1 = time.monotonic()
    await poller._fetch(spot_holder[0])
    elapsed2 = time.monotonic() - t1

    if poller.cache:
        print(f"✅ Top OI anchors: {len(poller.cache)} contracts in {elapsed2:.1f}s")
        for row in poller.cache[:5]:
            print(f"   {row['symbol']} | strike={row['strike']} | IV={row['implied_volatility']:.2f} | OI={row['open_interest']}")
    else:
        print(f"❌ No data in cache after fetch ({elapsed2:.1f}s)")


def _backend_is_alive() -> bool:
    """Return True if uvicorn backend is listening on port 8001."""
    try:
        with socket.create_connection(("127.0.0.1", 8001), timeout=0.5):
            return True
    except (ConnectionRefusedError, OSError):
        return False


async def main() -> None:
    print("=" * 55)
    print("  T2 / T3 POLLER — LONGBRIDGE CONNECTIVITY TEST")
    print("=" * 55)

    # ── 后端运行保护 ─────────────────────────────────────────────────────────
    # 此脚本直接调用长桥 REST，其请求数会和后端的叠加。
    # 如果后端同时在运行，合计频率可能超过 10次/秒，触发 301607 限频错误。
    if _backend_is_alive():
        print()
        print("❌ 检测到后端 uvicorn 正在 localhost:8001 运行！")
        print("   此脚本对长桥的请求会与后端叠加，可能超过 10次/秒限额。")
        print("   请先停止后端再运行此测试脚本：")
        print("     Get-Process uvicorn | Stop-Process -Force")
        print()
        sys.exit(1)
    print("✅ 后端未运行 — 安全，不会叠加配额")

    print("\n[*] Connecting to LongBridge QuoteContext...")
    try:
        ctx = make_ctx()
        print("✅ QuoteContext connected")
    except Exception as e:
        print(f"❌ QuoteContext FAILED: {e}")
        return

    # 极度保守的限速器：rate=2 + 后端停止，合计依然远低于 10次/秒上限
    limiter = APIRateLimiter(rate=2.0, burst=3, max_concurrent=2)

    await test_t2(ctx, limiter)
    await test_t3(ctx, limiter)

    print("\n" + "=" * 55)
    print("  TEST COMPLETE")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
