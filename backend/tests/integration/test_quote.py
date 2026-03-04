import time
import logging
from app.config import settings
from longport.openapi import QuoteContext, Config, SubType

logging.basicConfig(level=logging.INFO)

def test_quote():
    print("=== TEST 2: OPTION QUOTE (L1) ===")
    config = Config(
        app_key=settings.longport_app_key,
        app_secret=settings.longport_app_secret,
        access_token=settings.longport_access_token,
    )
    
    opt_sym = 'O:SPY260320C00680000' 
    
    ctx = QuoteContext(config)
    print(f"Connected to LongPort QuoteContext. Testing {opt_sym}")
    ctx.subscribe([opt_sym], [SubType.Quote])
    time.sleep(1.0)
    
    quotes = ctx.quote([opt_sym])
    if quotes:
        q = quotes[0]
        print(f"✅ Symbol        (symbol): {q.symbol}")
        print(f"✅ Strike Price  (行权价): {q.strike_price}")
        print(f"✅ Option Type   (看涨跌): {q.option_type.name}")
        print(f"✅ Last Done     (最新价): {q.last_done}")
        print(f"✅ Implied Vol   (IV隐含波动率): {q.implied_volatility}")
        print(f"✅ Open Interest (未平仓合约): {q.open_interest}")
        print(f"✅ Volume        (成交量): {q.volume}")
        print(f"✅ Bid           (买一价): {q.bid}")
        print(f"✅ Ask           (卖一价): {q.ask}")
    else:
        print(f"❌ ERROR: No quote data returned for {opt_sym}")

if __name__ == "__main__":
    test_quote()
