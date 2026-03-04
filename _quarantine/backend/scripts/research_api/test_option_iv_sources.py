"""
Test: Compare IV from all 3 available LongPort sources:
  1. REST  ctx.option_quote()    - per the LongPort option-quote API doc
  2. REST  ctx.calc_indexes()    - what iv_baseline_sync actually uses
  3. WS    SubType.Quote push    - empirically test if option_extend arrives

Per official doc (https://open.longportapp.com/zh-CN/docs/quote/pull/option-quote):
  OptionQuote.option_extend.implied_volatility is a decimal string (e.g. "0.592")

Run this script live during market hours to confirm which sources deliver IV.
"""
import asyncio
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, backend_dir)

from longport.openapi import QuoteContext, Config, SubType, CalcIndex
from app.config import settings

# ── Setup ──────────────────────────────────────────────────────────────────────
cfg = Config(
    app_key=settings.longport_app_key,
    app_secret=settings.longport_app_secret,
    access_token=settings.longport_access_token,
)
ctx = QuoteContext(cfg)

ws_quote_events: list[dict] = []

def on_quote(symbol: str, event: Any):
    opt_ext = getattr(event, 'option_extend', None)
    iv_from_ws = None
    if opt_ext:
        raw = getattr(opt_ext, 'implied_volatility', None)
        iv_from_ws = float(raw) if raw else None
    ws_quote_events.append({
        "symbol": symbol,
        "last_done": getattr(event, 'last_done', None),
        "option_extend_present": opt_ext is not None,
        "ws_iv": iv_from_ws,
    })

async def run():
    spot_sym = "SPY.US"
    today = datetime.now(ZoneInfo("US/Eastern")).date()

    # Get spot
    qres = ctx.quote([spot_sym])
    spot = float(qres[0].last_done)
    print(f"SPY Spot: {spot:.2f}")

    # Get ATM chain
    chains = ctx.option_chain_info_by_date(spot_sym, today)
    if not chains:
        print("ERROR: No option chain. Is market open?")
        return

    closest_strike = min([float(c.price) for c in chains], key=lambda x: abs(x - spot))
    atm = [c for c in chains if float(c.price) == closest_strike][0]
    call_sym = atm.call_symbol
    put_sym  = atm.put_symbol

    print(f"ATM Strike: {closest_strike}")
    print(f"Call: {call_sym}")
    print(f"Put:  {put_sym}\n")

    # ── SOURCE 1: REST option_quote() ─────────────────────────────────────────
    print("=" * 60)
    print("SOURCE 1: REST ctx.option_quote()")
    print("=" * 60)
    try:
        oqs = ctx.option_quote([call_sym, put_sym])
        for oq in oqs:
            ext = getattr(oq, 'option_extend', None)
            if ext:
                iv_raw = getattr(ext, 'implied_volatility', None)
                hv_raw = getattr(ext, 'historical_volatility', None)
                oi_raw = getattr(ext, 'open_interest', None)
                print(f"  {oq.symbol}")
                print(f"    implied_volatility  = {iv_raw}  → as float: {float(iv_raw) if iv_raw else 'N/A'}")
                print(f"    historical_volatility = {hv_raw}")
                print(f"    open_interest       = {oi_raw}")
                print(f"    last_done           = {oq.last_done}")
            else:
                print(f"  {oq.symbol}: option_extend = None!")
    except Exception as e:
        print(f"  option_quote() FAILED: {e}")

    # ── SOURCE 2: REST calc_indexes() ─────────────────────────────────────────
    print()
    print("=" * 60)
    print("SOURCE 2: REST ctx.calc_indexes() [what iv_baseline_sync uses]")
    print("=" * 60)
    try:
        results = ctx.calc_indexes(
            [call_sym, put_sym],
            [CalcIndex.ImpliedVolatility, CalcIndex.OpenInterest]
        )
        for item in results:
            iv_raw = item.implied_volatility
            oi_raw = item.open_interest
            # iv_baseline_sync divides by 100 — test if that is correct
            iv_as_stored = float(iv_raw) / 100.0 if iv_raw else None
            print(f"  {item.symbol}")
            print(f"    implied_volatility (raw)    = {iv_raw}")
            print(f"    implied_volatility (/100)   = {iv_as_stored}  ← what iv_baseline_sync stores")
            print(f"    open_interest               = {oi_raw}")
    except Exception as e:
        print(f"  calc_indexes() FAILED: {e}")

    # ── SOURCE 3: WS SubType.Quote (20s test) ─────────────────────────────────
    print()
    print("=" * 60)
    print("SOURCE 3: WS SubType.Quote push (listening 20s)")
    print("=" * 60)
    ctx.set_on_quote(on_quote)
    ctx.subscribe([call_sym, put_sym], [SubType.Quote])
    await asyncio.sleep(20)
    ctx.unsubscribe([call_sym, put_sym], [SubType.Quote])

    print(f"  Received {len(ws_quote_events)} WS Quote events")
    if ws_quote_events:
        with_ext   = [e for e in ws_quote_events if e["option_extend_present"]]
        without_ext = [e for e in ws_quote_events if not e["option_extend_present"]]
        with_iv    = [e for e in ws_quote_events if e["ws_iv"] is not None]
        print(f"    option_extend present : {len(with_ext)}/{len(ws_quote_events)}")
        print(f"    option_extend absent  : {len(without_ext)}/{len(ws_quote_events)}")
        print(f"    IV value present      : {len(with_iv)}/{len(ws_quote_events)}")
        if with_iv:
            print(f"    Sample WS IV values   : {[e['ws_iv'] for e in with_iv[:3]]}")
        print()
        print("  Last 3 WS events:")
        for ev in ws_quote_events[-3:]:
            print(f"    {ev}")

    print()
    print("=" * 60)
    print("CONCLUSION:")
    print("  option_quote() IV:  check SOURCE 1 above")
    print("  calc_indexes() IV:  check SOURCE 2 above")
    print("  WS SubType.Quote:   IV present in", sum(1 for e in ws_quote_events if e['ws_iv']), "of", len(ws_quote_events), "pushes")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run())
