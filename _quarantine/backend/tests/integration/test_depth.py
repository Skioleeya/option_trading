import time
import logging
from app.config import settings
from longport.openapi import QuoteContext, Config, SubType

logging.basicConfig(level=logging.INFO)

def test_depth():
    print("=== TEST 3: L2 ORDER BOOK DEPTH ===")
    config = Config(
        app_key=settings.longport_app_key,
        app_secret=settings.longport_app_secret,
        access_token=settings.longport_access_token,
    )
    
    opt_sym = 'O:SPY260320C00680000'
    
    ctx = QuoteContext(config)
    print(f"Connected to LongPort QuoteContext. Testing depth for {opt_sym}")
    ctx.subscribe([opt_sym], [SubType.Depth])
    time.sleep(2.0)
    
    depth = ctx.depth(opt_sym)
    if depth:
        print("✅ Depth Data Retrieved!")
        
        print("\n  --- BIDS (买盘) ---")
        for i, b in enumerate(depth.bids[:5]):
            print(f"  Bid {i+1}: Price={b.price}, Size={b.volume}")
            
        print("\n  --- ASKS (卖盘) ---")
        for i, a in enumerate(depth.asks[:5]):
            print(f"  Ask {i+1}: Price={a.price}, Size={a.volume}")
            
        if depth.bids and depth.asks:
            bbo_imbalance = (depth.bids[0].volume - depth.asks[0].volume) / (depth.bids[0].volume + depth.asks[0].volume + 1e-9)
            print(f"\n✅ Computed BBO Imbalance: {bbo_imbalance:.4f}")
    else:
        print(f"❌ ERROR: No depth data returned for {opt_sym}")

if __name__ == "__main__":
    test_depth()
