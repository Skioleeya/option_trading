import asyncio
import logging
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

# Ensure we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from longport.openapi import QuoteContext, Config, SubType
from app.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_longport_data")

def on_quote(symbol: str, event: Any):
    logger.info(f"[QUOTE] {symbol}: Last Price={event.last_done}, Volume={event.volume}")

def on_depth(symbol: str, event: Any):
    logger.info(f"[DEPTH] {symbol}: Received Depth update")
    logger.info(f"  RAW DEPTH: {event}")
    # Log details of Bid/Ask depth
    try:
        if hasattr(event, 'bid'):
            for d in event.bid:
                logger.info(f"  BID: Pos={d.position}, Price={d.price}, Vol={d.volume}")
        if hasattr(event, 'ask'):
            for d in event.ask:
                logger.info(f"  ASK: Pos={d.position}, Price={d.price}, Vol={d.volume}")
    except Exception as e:
        logger.warning(f"Error parsing depth: {e}")

def on_trade(symbol: str, event: Any):
    logger.info(f"[TRADE] {symbol}: Received Trade update")
    logger.info(f"  RAW TRADE: {event}")
    # Log details of each trade, especially direction
    try:
        if hasattr(event, 'trades'):
            for t in event.trades:
                logger.info(f"  TRADE: Price={t.price}, Vol={t.volume}, Dir={t.direction}, Type={t.trade_type}")
    except Exception as e:
        logger.warning(f"Error parsing trade: {e}")

async def run_test():
    try:
        config = Config(
            app_key=settings.longport_app_key,
            app_secret=settings.longport_app_secret,
            access_token=settings.longport_access_token,
        )
        ctx = QuoteContext(config)

        # 1. Setup Callbacks
        ctx.set_on_quote(on_quote)
        ctx.set_on_depth(on_depth)
        ctx.set_on_trades(on_trade)

        # 2. Identify target symbols (SPY + some options)
        spot_sym = "SPY.US"
        
        # Get options for today (0DTE)
        today = datetime.now(ZoneInfo("US/Eastern")).date()
        logger.info(f"Fetching options for SPY.US on {today}...")
        chains = ctx.option_chain_info_by_date(spot_sym, today)
        
        if not chains:
            logger.error("No option chains found for today. Is it a trading day?")
            # Attempt to find next valid expiry if today has none
            # (Just for robustness if the test is run off-market hours)
        
        # Select 2 ATM options (1 call, 1 put)
        quotes = ctx.quote([spot_sym])
        spot_price = float(quotes[0].last_done)
        logger.info(f"Current SPY Spot: {spot_price}")

        # Simple ATM selection
        closest_strike = min([float(c.price) for c in chains], key=lambda x: abs(x - spot_price))
        atm_chain = [c for c in chains if float(c.price) == closest_strike][0]
        
        test_symbols = [spot_sym, atm_chain.call_symbol, atm_chain.put_symbol]
        logger.info(f"Subscribing to: {test_symbols}")

        # 3. Subscribe with all requested subtypes
        sub_types = [SubType.Quote, SubType.Depth, SubType.Trade]
        ctx.subscribe(test_symbols, sub_types)

        # 4. Wait and observe for 30 seconds
        logger.info("Listening for updates (30s)...")
        await asyncio.sleep(30)

        # 5. Cleanup
        ctx.unsubscribe(test_symbols, sub_types)
        logger.info("Test complete.")

    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_test())
