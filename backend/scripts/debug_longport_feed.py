import asyncio
import os
import sys
import logging
from pathlib import Path

# Add backend root to path so we can import app
backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))

# MANUALLY LOAD .ENV to override "test" environment variables
dot_env = backend_root / ".env"
if dot_env.exists():
    with open(dot_env, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                # Remove quotes if present
                v = v.strip("'").strip('"')
                os.environ[k] = v
                # logger.info(f"Loaded {k} from .env") # Don't log values

from app.config import settings
from longport.openapi import QuoteContext, Config, SubType

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LongportDebug")

async def run_debug():
    # Use credentials from app settings (now updated by .env)
    app_key = settings.longport_app_key
    app_secret = settings.longport_app_secret
    access_token = settings.longport_access_token

    if not all([app_key, app_secret, access_token]) or app_key == "test":
        logger.error(f"Invalid Longport credentials in settings: {app_key}")
        return

    logger.info(f"Using App Key: {app_key[:4]}***")

    config = Config(app_key=app_key, app_secret=app_secret, access_token=access_token)
    try:
        ctx = QuoteContext(config)
    except Exception as e:
        logger.error(f"Failed to create QuoteContext: {e}")
        return

    def on_quote(symbol, quote):
        logger.info(f"QUOTE [{symbol}]: last={getattr(quote, 'last_done', 'N/A')}, vol={getattr(quote, 'volume', 'N/A')}, timestamp={getattr(quote, 'timestamp', 'N/A')}")

    def on_trades(symbol, event):
        trades = getattr(event, 'trades', [])
        logger.info(f"TRADES [{symbol}]: count={len(trades)}")
        for i, t in enumerate(trades[:3]):
            dir_str = str(getattr(t, 'direction', '0'))
            logger.info(f"  TRADE {i}: price={getattr(t, 'price', 'N/A')}, vol={getattr(t, 'volume', 'N/A')}, dir={dir_str}, time={getattr(t, 'timestamp', 'N/A')}")

    ctx.set_on_quote(on_quote)
    ctx.set_on_trades(on_trades)

    # Subscribe to SPY and some ATM options
    symbols = ["SPY.US"]
    
    try:
        from datetime import datetime
        # Check if market is open (just for info)
        logger.info(f"Fetching option chain for SPY.US...")
        # Note: Longport might require date to be current or next trading day
        # If today is weekend, it might return empty.
        chain = ctx.option_chain_info_by_date("SPY.US", datetime.now().date())
        if chain:
            # Pick a few ATM options
            mid = len(chain) // 2
            for i in range(max(0, mid-2), min(len(chain), mid+2)):
                s = chain[i]
                if hasattr(s, 'call_symbol') and s.call_symbol:
                    symbols.append(s.call_symbol)
                if hasattr(s, 'put_symbol') and s.put_symbol:
                    symbols.append(s.put_symbol)
    except Exception as e:
        logger.warning(f"Failed to find option symbols (market might be closed or API error): {e}")

    logger.info(f"Subscribing to: {symbols}")
    ctx.subscribe(symbols, [SubType.Quote, SubType.Trade])

    logger.info("Listening for 60 seconds... (Wait for trade events)")
    await asyncio.sleep(60)
    logger.info("Done.")

if __name__ == "__main__":
    asyncio.run(run_debug())
