import time
import logging
from app.config import settings
from longport.openapi import QuoteContext, Config, SubType

logging.basicConfig(level=logging.INFO)

def test_trades():
    print("=== TEST 4: L2 TICK / ACTIVE TRADES ===")
    config = Config(
        app_key=settings.longport_app_key,
        app_secret=settings.longport_app_secret,
        access_token=settings.longport_access_token,
    )
    
    opt_sym = 'O:SPY260320C00680000'
    
    ctx = QuoteContext(config)
    print(f"Connected to LongPort QuoteContext. Testing trades for {opt_sym}")
    ctx.subscribe([opt_sym], [SubType.Trade])
    time.sleep(2.0)
    
    trades = ctx.trades(opt_sym, 10)
    if trades:
        print(f"✅ Trades Retrieved ({len(trades)} ticks)")
        buy_vol = 0
        sell_vol = 0
        
        for index, t in enumerate(trades):
            dir_name = t.direction.name if t.direction else "UNKNOWN"
            print(f"  Trade {index+1}: Price={t.price}, Vol={t.volume}, Direction={dir_name}")
            
            if dir_name == "Up":
                buy_vol += t.volume
            elif dir_name == "Down":
                sell_vol += t.volume
                
        print(f"\n✅ Aggregation: Active Buy Vol = {buy_vol}, Active Sell Vol = {sell_vol}")
        if (buy_vol + sell_vol) > 0:
            toxicity = (buy_vol - sell_vol) / (buy_vol + sell_vol)
            print(f"✅ Partial Toxicity / VPIN proxy: {toxicity:.4f}")
    else:
        print(f"❌ ERROR: No trade data returned for {opt_sym}")

if __name__ == "__main__":
    test_trades()
