import asyncio
import logging
import sys
import os
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from typing import Any

# Ensure we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from longport.openapi import QuoteContext, Config, Market
from app.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_market_day_data")

async def test_market_temp(ctx: QuoteContext):
    logger.info("--- Testing Market Temperature (US) ---")
    try:
        temp = ctx.market_temperature(Market.US)
        if temp:
            logger.info(f"[SUCCESS] Current Market Temp: {temp.temperature}, Sentiment: {temp.sentiment}, Valuation: {temp.valuation}")
            logger.info(f"  Description: {temp.description}")
        else:
            logger.warning("[EMPTY] Market Temperature returned nothing")
    except Exception as e:
        logger.error(f"[ERROR] Market Temperature failed: {e}")

    logger.info("--- Testing History Market Temperature (US) ---")
    try:
        # Using a wider range as per example
        start = date(2024, 1, 1)
        end = date(2025, 1, 1)
        hist = ctx.history_market_temperature(Market.US, start, end)
        if hist and hasattr(hist, 'list'):
            logger.info(f"[SUCCESS] History Market Temp: {len(hist.list)} records")
            if hist.list:
                last = hist.list[-1]
                logger.info(f"  Latest Hist Temp: {last.temperature} at {last.timestamp}")
        else:
            logger.warning(f"[EMPTY] History Market Temperature returned nothing for {start} to {end}")
    except Exception as e:
        logger.error(f"[ERROR] History Market Temperature failed: {e}")

async def test_intraday(ctx: QuoteContext, symbol: str):
    logger.info(f"--- Testing Intraday for {symbol} ---")
    try:
        lines = ctx.intraday(symbol)
        if lines:
            logger.info(f"[SUCCESS] Intraday for {symbol}: {len(lines)} lines")
            last = lines[-1]
            logger.info(f"  Latest Price: {last.price}, Vol: {last.volume}, Time: {last.timestamp}")
        else:
            logger.warning(f"[EMPTY] Intraday returned nothing for {symbol}")
    except Exception as e:
        logger.error(f"[ERROR] Intraday failed for {symbol}: {e}")

async def run_test():
    try:
        config = Config(
            app_key=settings.longport_app_key,
            app_secret=settings.longport_app_secret,
            access_token=settings.longport_access_token,
        )
        ctx = QuoteContext(config)

        # 1. Market Level
        await test_market_temp(ctx)

        # 2. Symbol Level (SPY + 0DTE Option)
        spot_sym = "SPY.US"
        today = datetime.now(ZoneInfo("US/Eastern")).date()
        chains = ctx.option_chain_info_by_date(spot_sym, today)
        
        if chains:
            quotes = ctx.quote([spot_sym])
            spot_price = float(quotes[0].last_done)
            closest_strike = min([float(c.price) for c in chains], key=lambda x: abs(x - spot_price))
            atm_chain = [c for c in chains if float(c.price) == closest_strike][0]
            call_sym = atm_chain.call_symbol
            
            await test_intraday(ctx, spot_sym)
            await test_intraday(ctx, call_sym)
        else:
            logger.warning("No option chains found for today, skipping option intraday test.")
            await test_intraday(ctx, spot_sym)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_test())
