"""
Test: What fields does LongPort actually push for Option Quotes via WebSocket?

This script subscribes to:
  1. SubType.Quote  - standard quote push
  2. SubType.Depth  - order book push

And prints EVERY field it receives for the ATM option, 
so we can empirically verify if implied_volatility is present.
"""
import asyncio
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, backend_dir)

from longport.openapi import QuoteContext, Config, SubType
from app.config import settings

quote_events = []
depth_events = []

def on_quote(symbol: str, event: Any):
    ts = datetime.now().strftime("%H:%M:%S.%f")
    print(f"\n{'='*60}")
    print(f"[{ts}] QUOTE PUSH for {symbol}")
    print(f"  All attrs: {[a for a in dir(event) if not a.startswith('_')]}")
    for attr in [a for a in dir(event) if not a.startswith('_')]:
        try:
            val = getattr(event, attr)
            if not callable(val):
                print(f"  {attr:30s} = {val}")
        except Exception:
            pass
    # Specifically check option_extend
    opt_ext = getattr(event, 'option_extend', None)
    if opt_ext:
        print(f"\n  [option_extend] attrs: {[a for a in dir(opt_ext) if not a.startswith('_')]}")
        for attr in [a for a in dir(opt_ext) if not a.startswith('_')]:
            try:
                val = getattr(opt_ext, attr)
                if not callable(val):
                    print(f"    {attr:30s} = {val}")
            except Exception:
                pass
    else:
        print("  [option_extend] = None / Not present!")
    quote_events.append(symbol)

def on_depth(symbol: str, event: Any):
    ts = datetime.now().strftime("%H:%M:%S.%f")
    print(f"\n{'='*60}")
    print(f"[{ts}] DEPTH PUSH for {symbol}")
    bids = getattr(event, 'bids', []) or []
    asks = getattr(event, 'asks', []) or []
    if bids:
        b0 = bids[0]
        print(f"  Best BID: price={getattr(b0,'price',None)} vol={getattr(b0,'volume',None)}")
    if asks:
        a0 = asks[0]
        print(f"  Best ASK: price={getattr(a0,'price',None)} vol={getattr(a0,'volume',None)}")
    depth_events.append(symbol)

async def run():
    config = Config(
        app_key=settings.longport_app_key,
        app_secret=settings.longport_app_secret,
        access_token=settings.longport_access_token,
    )
    ctx = QuoteContext(config)
    ctx.set_on_quote(on_quote)
    ctx.set_on_depth(on_depth)

    spot_sym = "SPY.US"
    today = datetime.now(ZoneInfo("US/Eastern")).date()

    # Get ATM strike
    quotes = ctx.quote([spot_sym])
    spot = float(quotes[0].last_done)
    print(f"SPY Spot: {spot}")

    chains = ctx.option_chain_info_by_date(spot_sym, today)
    if not chains:
        print("ERROR: No option chain data. Is market open?")
        return

    closest_strike = min([float(c.price) for c in chains], key=lambda x: abs(x - spot))
    atm = [c for c in chains if float(c.price) == closest_strike][0]

    call_sym = atm.call_symbol
    put_sym  = atm.put_symbol
    print(f"ATM Strike: {closest_strike}")
    print(f"Call: {call_sym}")
    print(f"Put:  {put_sym}")

    # Also test REST option_quote (non-WS)
    print("\n=== REST option_quote() result ===")
    try:
        opt_quotes = ctx.option_quote([call_sym, put_sym])
        for oq in opt_quotes:
            print(f"\nREST {oq.symbol}:")
            for attr in [a for a in dir(oq) if not a.startswith('_')]:
                try:
                    val = getattr(oq, attr)
                    if not callable(val):
                        print(f"  {attr:30s} = {val}")
                except Exception:
                    pass
    except Exception as e:
        print(f"option_quote() error: {e}")

    # Subscribe WS: Quote + Depth
    test_syms = [call_sym, put_sym]
    print(f"\n=== Subscribing WS Quote+Depth for {test_syms} ===")
    ctx.subscribe(test_syms, [SubType.Quote, SubType.Depth])

    print("Listening for 20 seconds for live pushes...\n")
    await asyncio.sleep(20)

    ctx.unsubscribe(test_syms, [SubType.Quote, SubType.Depth])
    print(f"\n=== SUMMARY ===")
    print(f"Quote events received: {len(quote_events)}")
    print(f"Depth events received: {len(depth_events)}")

if __name__ == "__main__":
    asyncio.run(run())
