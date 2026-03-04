import asyncio
import logging
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

# Ensure we can import from app
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, backend_dir)

from longport.openapi import QuoteContext, Config, SubType
from app.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sandbox_depth")

def on_depth(symbol: str, event: Any):
    logger.info(f"\n[{symbol}] DEPTH PUSH:")
def on_depth(symbol: str, event: Any):
    logger.info(f"\n[{symbol}] DEPTH PUSH:")
    try:
        if hasattr(event, 'bids') and event.bids:
            for b in event.bids[:5]:
                print(f"  [BID] pos: {getattr(b, 'position', 0):2d} | price: {getattr(b, 'price', 0):8.2f} | count: {getattr(b, 'order_num', 0):3d} | vol: {getattr(b, 'volume', 0)}")
        else:
            print("  [BID] Empty")
            
        print("  ---")

        if hasattr(event, 'asks') and event.asks:
            for a in event.asks[:5]:
                print(f"  [ASK] pos: {getattr(a, 'position', 0):2d} | price: {getattr(a, 'price', 0):8.2f} | count: {getattr(a, 'order_num', 0):3d} | vol: {getattr(a, 'volume', 0)}")
        else:
            print("  [ASK] Empty")
    except Exception as e:
        logger.warning(f"Error parsing depth: {e}")

async def run_sandbox():
    try:
        config = Config(
            app_key=settings.longport_app_key,
            app_secret=settings.longport_app_secret,
            access_token=settings.longport_access_token,
        )
        ctx = QuoteContext(config)

        # 1. Setup Callback
        ctx.set_on_depth(on_depth)

        spot_sym = "SPY.US"
        today = datetime.now(ZoneInfo("US/Eastern")).date()
        
        logger.info(f"Looking for 0DTE options on {today}...")
        chains = ctx.option_chain_info_by_date(spot_sym, today)
        
        if not chains:
            logger.error("No option chains found. Ensure market is open and date is valid.")
            return
            
        quotes = ctx.quote([spot_sym])
        spot_price = float(quotes[0].last_done)
        logger.info(f"Current SPY Spot: {spot_price}")

        # Pick nearest ATM option
        closest_strike = min([float(c.price) for c in chains], key=lambda x: abs(x - spot_price))
        atm_chain = [c for c in chains if float(c.price) == closest_strike][0]
        
        # For testing Depth, we just subscribe to Spot + ATM Call
        test_symbols = [spot_sym, atm_chain.call_symbol]
        
        logger.info(f"==> Subscribing Depth for: {test_symbols}")
        ctx.subscribe(test_symbols, [SubType.Depth])

        logger.info("Listening for 15 seconds...\n")
        await asyncio.sleep(15)

        ctx.unsubscribe(test_symbols, [SubType.Depth])
        logger.info("Sandbox complete.")

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_sandbox())
