import time
from longport.openapi import QuoteContext, Config, SubType
import re

def on_quote(symbol, event):
    pass

def on_depth(symbol, event):
    print(f"[MVP] DEPTH | {symbol} | bids: {len(event.bids)} asks: {len(event.asks)}")

def main():
    config = Config.from_env()
    ctx = QuoteContext(config)
    ctx.set_on_quote(on_quote)
    ctx.set_on_depth(on_depth)

    # Let's generate 100 symbols for SPY options
    print("Generating 100 valid-looking SPY symbols...")
    symbols = []
    # Just guess some SPY strikes around 650
    for strike in range(600, 700):
        symbols.append(f"SPY260325C{strike}000.US")
    
    ctx.subscribe(symbols, [SubType.Depth])
    print("[MVP] Subscribed to 100 symbols. Waiting 30s for stream...")
    for i in range(10):
        time.sleep(3)
        print(f"[MVP] Still listening... {30 - (i+1)*3}s remaining")

if __name__ == "__main__":
    main()
