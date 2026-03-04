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
logger = logging.getLogger("sandbox_trade")

def on_trade(symbol: str, event: Any):
    logger.info(f"\n[{symbol}] TRADE PUSH:")
    # A single Trade push might contain an array of trades
    try:
        trades = getattr(event, 'trades', [])
        if not trades:
            logger.info("  [TRADE] Empty array")
            return
            
        for idx, t in enumerate(trades[:5]):
            price = getattr(t, 'price', 0)
            vol = getattr(t, 'volume', 0)
            timestamp = getattr(t, 'timestamp', 0)
            trade_type = getattr(t, 'trade_type', 'N/A')
            direction = getattr(t, 'direction', 'N/A') 
            
            # direction: 0 (Neutral), 1 (Buy/Take Ask), 2 (Sell/Hit Bid)
            dir_str = "NEUTRAL"
            if str(direction) == "1": dir_str = "BUY(Ask)"
            elif str(direction) == "2": dir_str = "SELL(Bid)"
            
            print(f"  [{idx:2d}] TS: {timestamp} | P: {price:8.2f} | V: {vol:4d} | Dir: {dir_str} | Type: {trade_type}")
            
        if len(trades) > 5:
            print(f"  ... and {len(trades) - 5} more trades in this push.")
            
    except Exception as e:
        logger.warning(f"Error parsing trade: {e}")

async def run_sandbox():
    try:
        config = Config(
            app_key=settings.longport_app_key,
            app_secret=settings.longport_app_secret,
            access_token=settings.longport_access_token,
        )
        ctx = QuoteContext(config)

        # 1. Setup Callback
        ctx.set_on_trades(on_trade)

        spot_sym = "SPY.US"
        today = datetime.now(ZoneInfo("US/Eastern")).date()
        
        logger.info(f"Looking for 0DTE options on {today}...")
        chains = ctx.option_chain_info_by_date(spot_sym, today)
        
        if not chains:
            logger.error("No option chains found (market might be fully closed and cleared).")
            return
            
        quotes = ctx.quote([spot_sym])
        spot_price = float(quotes[0].last_done)
        logger.info(f"Current SPY Spot: {spot_price}")

        closest_strike = min([float(c.price) for c in chains], key=lambda x: abs(x - spot_price))
        atm_chain = [c for c in chains if float(c.price) == closest_strike][0]
        
        test_symbols = [spot_sym, atm_chain.call_symbol]
        logger.info(f"==> REST: Fetching historical trades for today (Intraday)")
        
        # Test the REST API for historical intraday trades (often works after hours)
        # 1000 trades max per API call usually
        try:
            hist_trades_spot = ctx.trades(spot_sym, 10)
            logger.info(f"\n[REST] Got {len(hist_trades_spot)} recent trades for {spot_sym}")
            for t in hist_trades_spot[:3]:
                logger.info(f"  P: {t.price} | V: {t.volume} | Dir: {t.direction}")
                
            hist_trades_opt = ctx.trades(atm_chain.call_symbol, 10)
            logger.info(f"\n[REST] Got {len(hist_trades_opt)} recent trades for {atm_chain.call_symbol}")
            for t in hist_trades_opt[:3]:
                logger.info(f"  P: {t.price} | V: {t.volume} | Dir: {t.direction}")
        except Exception as e:
            logger.warning(f"Failed to fetch REST trades: {e}")

        logger.info(f"\n==> WS: Subscribing SubType.Trade for: {test_symbols}")
        ctx.subscribe(test_symbols, [SubType.Trade])

        logger.info("Listening for WS pushes for 15 seconds (might be quiet after hours)...\n")
        await asyncio.sleep(15)

        ctx.unsubscribe(test_symbols, [SubType.Trade])
        logger.info("Sandbox complete.")

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_sandbox())
