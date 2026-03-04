import time
import logging
from app.config import settings
from longport.openapi import QuoteContext, Config, SubType
import atexit

logging.basicConfig(level=logging.INFO)

def test_all():
    print("=== INITIALIZING LONGPORT CONNECTION ===")
    config = Config(
        app_key=settings.longport_app_key,
        app_secret=settings.longport_app_secret,
        access_token=settings.longport_access_token,
    )
    
    ctx = QuoteContext(config)
    print("Connected to LongPort QuoteContext.\n")
    
    spot_sym = 'SPY.US'
    
    print("Fetching active option dates for SPY...")
    time.sleep(0.5) # respect 10 calls / sec limit
    dates = ctx.option_chain_expiry_date_list(spot_sym)
    if not dates:
        print("❌ ERROR: No option dates found.")
        return
        
    time.sleep(0.5)
    chain = ctx.option_chain_info_by_date(spot_sym, dates[0])
    if not chain:
        print("❌ ERROR: No option chain info found.")
        return
        
    opt_sym = chain[len(chain)//2].call_symbol
    print(f"🎯 Auto-selected valid option symbol: {opt_sym}\n")
    
    print("=== SUBSCRIBE ===")
    time.sleep(0.5)
    # The limit is 500 targets; we are subscribing to 2.
    ctx.subscribe([spot_sym, opt_sym], [SubType.Quote, SubType.Depth, SubType.Trade])
    
    print("Waiting 2 seconds to accumulate data payload from WebSocket...")
    time.sleep(2.0)
    
    print("\n=== TEST 1: SPOT LEVEL (SPY.US) ===")
    time.sleep(0.2)
    quotes = ctx.quote([spot_sym])
    if quotes:
        q = quotes[0]
        print(f"✅ Symbol     : {q.symbol}")
        print(f"✅ Last Done  : {q.last_done}")
        print(f"✅ Prev Close : {q.prev_close}")
        print(f"✅ Volume     : {q.volume}")
        print(f"✅ Turnover   : {q.turnover}")
    else:
        print("❌ ERROR: No quote data returned for SPY.US")

    print(f"\n=== TEST 2: OPTION QUOTE (L1) - {opt_sym} ===")
    time.sleep(0.5) # respect rate limit
    opt_quotes = ctx.option_quote([opt_sym])
    if opt_quotes:
        oq = opt_quotes[0]
        print(f"✅ Direction    : {str(oq.direction) if getattr(oq, 'direction', None) else str(oq.contract_type)}")
        print(f"✅ Last Done    : {oq.last_done}")
        print(f"✅ Implied Vol  : {oq.implied_volatility}")
        print(f"✅ Open Interest: {oq.open_interest}")
        print(f"✅ Volume       : {oq.volume}")
    else:
        print(f"❌ ERROR: No quote data returned for {opt_sym}")

    print(f"\n=== TEST 3: L2 ORDER BOOK DEPTH - {opt_sym} ===")
    time.sleep(0.2)
    depth = ctx.depth(opt_sym)
    if depth:
        print("✅ Depth Data Retrieved!")
        if depth.bids and depth.asks:
            print(f"  Top Bid: {depth.bids[0].price} x {depth.bids[0].volume}")
            print(f"  Top Ask: {depth.asks[0].price} x {depth.asks[0].volume}")
            bbo_imbalance = (depth.bids[0].volume - depth.asks[0].volume) / (depth.bids[0].volume + depth.asks[0].volume + 1e-9)
            print(f"✅ Computed BBO Imbalance: {bbo_imbalance:.4f}")
    else:
        print(f"❌ ERROR: No depth data returned for {opt_sym}")
        
    print(f"\n=== TEST 4: L2 TICK / ACTIVE TRADES - {opt_sym} ===")
    time.sleep(0.2)
    trades = ctx.trades(opt_sym, 10)
    if trades:
        print(f"✅ Trades Retrieved ({len(trades)} ticks)")
        buy_vol = 0
        sell_vol = 0
        for i, t in enumerate(trades[:3]):
            dir_name = t.direction.name if t.direction else "UNKNOWN"
            print(f"  Trade {i+1}: Price={t.price}, Vol={t.volume}, Dir={dir_name}")
            
        for t in trades:
            dir_name = t.direction.name if t.direction else "UNKNOWN"
            if dir_name == "Up":
                buy_vol += t.volume
            elif dir_name == "Down":
                sell_vol += t.volume
                
        if (buy_vol + sell_vol) > 0:
            toxicity = (buy_vol - sell_vol) / (buy_vol + sell_vol)
            print(f"✅ Proxy Toxicity Score: {toxicity:.4f}")
    else:
        print(f"❌ ERROR: No trade data returned for {opt_sym}")

if __name__ == "__main__":
    try:
        test_all()
    except KeyboardInterrupt:
        print("Interrupted by user.")
