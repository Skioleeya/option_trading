import sys
import time
from dotenv import load_dotenv
from longport.openapi import Config, QuoteContext, SubType, PushQuote

def main():
    load_dotenv()
    config = Config.from_env()
    ctx = QuoteContext(config)

    def on_quote(symbol, event):
        print(f"[MVP] QUOTE | {symbol} | bid: {getattr(event, 'bid', 'None')} ask: {getattr(event, 'ask', 'None')}")
        print(f"      dirs: {[d for d in dir(event) if not d.startswith('_')]}")

    def on_depth(symbol, event):
        print(f"[MVP] DEPTH | {symbol} | bids: {getattr(event, 'bids', [])} asks: {getattr(event, 'asks', [])}")

    ctx.set_on_quote(on_quote)
    ctx.set_on_depth(on_depth)

    symbols = ["SPY260325C658000.US"]
    
    ctx.subscribe(symbols, [SubType.Quote, SubType.Depth])
    print("[MVP] Waiting for streaming events for 30 seconds...")
    for i in range(10):
        time.sleep(3)
        print(f"[MVP] Still listening... {30 - (i+1)*3}s remaining")
    print("[MVP] Finished.")

if __name__ == "__main__":
    main()
