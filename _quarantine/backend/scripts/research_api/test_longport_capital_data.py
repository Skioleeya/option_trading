import asyncio
import logging
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

# Ensure we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from longport.openapi import QuoteContext, Config
from app.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_capital_data")

async def test_capital(ctx: QuoteContext, symbol: str):
    logger.info(f"--- Testing {symbol} ---")
    
    # 1. Test Capital Flow Intraday
    try:
        flow = ctx.capital_flow(symbol)
        if flow:
            logger.info(f"[SUCCESS] Capital Flow for {symbol}: {len(flow)} lines")
            # Log the latest line
            last = flow[-1]
            logger.info(f"  Latest Inflow: {last.inflow}, Time: {last.timestamp}")
        else:
            logger.warning(f"[EMPTY] Capital Flow returned nothing for {symbol}")
    except Exception as e:
        logger.error(f"[ERROR] Capital Flow failed for {symbol}: {e}")

    # 2. Test Capital Distribution
    try:
        dist = ctx.capital_distribution(symbol)
        if dist:
            logger.info(f"[SUCCESS] Capital Distribution for {symbol}")
            logger.info(f"  In: Small={dist.capital_in.small}, Medium={dist.capital_in.medium}, Large={dist.capital_in.large}")
            logger.info(f"  Out: Small={dist.capital_out.small}, Medium={dist.capital_out.medium}, Large={dist.capital_out.large}")
        else:
            logger.warning(f"[EMPTY] Capital Distribution returned nothing for {symbol}")
    except Exception as e:
        logger.error(f"[ERROR] Capital Distribution failed for {symbol}: {e}")

async def run_test():
    try:
        config = Config(
            app_key=settings.longport_app_key,
            app_secret=settings.longport_app_secret,
            access_token=settings.longport_access_token,
        )
        ctx = QuoteContext(config)

        # 1. Identify target symbols (SPY + some options)
        spot_sym = "SPY.US"
        
        # Get options for today (0DTE)
        today = datetime.now(ZoneInfo("US/Eastern")).date()
        chains = ctx.option_chain_info_by_date(spot_sym, today)
        
        if not chains:
            logger.error("No option chains found for today.")
            return

        # Select 1 ATM Call
        quotes = ctx.quote([spot_sym])
        spot_price = float(quotes[0].last_done)
        closest_strike = min([float(c.price) for c in chains], key=lambda x: abs(x - spot_price))
        atm_chain = [c for c in chains if float(c.price) == closest_strike][0]
        call_sym = atm_chain.call_symbol

        # Run tests
        await test_capital(ctx, spot_sym)
        await test_capital(ctx, call_sym)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_test())
