import time
from longport.openapi import QuoteContext, Config, SubType
import re

def on_quote(symbol, event):
    print(f"[QUOTE] {symbol} | bid: {event.bid} ask: {event.ask} last: {event.last_done}")

def on_depth(symbol, event):
    bid = event.bids[0].price if event.bids else 0.0
    ask = event.asks[0].price if event.asks else 0.0
    print(f"[DEPTH] {symbol} | bid: {bid} ask: {ask}")

def main():
    config = Config.from_env()
    ctx = QuoteContext(config)
    ctx.set_on_quote(on_quote)
    ctx.set_on_depth(on_depth)

    symbols = ["SPY260325C657000.US"]
    ctx.subscribe(symbols, [SubType.Quote, SubType.Depth])
    print("[MVP] Subscribed to SPY ATM. Waiting 15s...")
    time.sleep(15)

if __name__ == "__main__":
    main()
