import time
import logging
from app.config import settings
from longport.openapi import QuoteContext, Config, SubType

logging.basicConfig(level=logging.INFO)

def test_spot():
    print("=== TEST 1: SPOT LEVEL (SPY.US) ===")
    config = Config(
        app_key=settings.longport_app_key,
        app_secret=settings.longport_app_secret,
        access_token=settings.longport_access_token,
    )
    
    ctx = QuoteContext(config)
    print("Connected to LongPort QuoteContext.")
    symbols = ['SPY.US']
    ctx.subscribe(symbols, [SubType.Quote])
    time.sleep(1.0)
    
    quotes = ctx.quote(symbols)
    if quotes:
        q = quotes[0]
        print(f"✅ Symbol     (symbol) : {q.symbol}")
        print(f"✅ Last Done (价格)    : {q.last_done}")
        print(f"✅ Prev Close (昨收)   : {q.prev_close}")
        print(f"✅ Volume    (成交量)  : {q.volume}")
        print(f"✅ Turnover  (成交额)  : {q.turnover}")
    else:
        print("❌ ERROR: No quote data returned for SPY.US")

if __name__ == "__main__":
    test_spot()
