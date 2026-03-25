import os
import sys
import time
from dotenv import load_dotenv
from longport.openapi import Config, QuoteContext, SubType, PushQuote

def main():
    load_dotenv()
    try:
        config = Config.from_env()
        ctx = QuoteContext(config)
        print("[MVP] Connected to LongPort OpenAPI.")
    except Exception as e:
        print(f"[MVP] Connection failed: {e}")
        return

    def on_quote(symbol, event):
        print(f"[MVP] QUOTE | {symbol} | {event}")

    def on_depth(symbol, event):
        print(f"[MVP] DEPTH | {symbol} | Bid: {getattr(event, 'ask', [])} Ask: {getattr(event, 'bid', [])}")
        
    def on_trade(symbol, event):
        print(f"[MVP] TRADE | {symbol} | {event}")

    ctx.set_on_quote(on_quote)
    ctx.set_on_depth(on_depth)
    ctx.set_on_trades(on_trade)

    symbols = ["SPY.US", "SPY260325C658000.US", "SPY260325P658000.US"]
    print(f"[MVP] Subscribing to {symbols} ...")
    
    try:
        ctx.subscribe(symbols, [SubType.Quote, SubType.Depth, SubType.Trade])
        print("[MVP] Subscription sent successfully. Waiting 15 seconds for events...")
    except Exception as e:
        print(f"[MVP] Subscription failed: {e}")
        return

    for i in range(15):
        time.sleep(1)
        sys.stdout.flush()

    print("[MVP] Test finished.")

if __name__ == "__main__":
    main()
