import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any
import json
import os
import sys

# Add backend to path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from longport.openapi import Config, QuoteContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VolumeResearch")

async def research_volume_distribution():
    """
    Fetches SPY 0DTE option chain volume distribution (+/- 70 strikes).
    Outputs a summary and JSON data for analysis.
    """
    try:
        # 1. Initialize Longport
        config = Config(
            app_key=settings.longport_app_key,
            app_secret=settings.longport_app_secret,
            access_token=settings.longport_access_token,
        )
        ctx = QuoteContext(config)
        logger.info("Longport QuoteContext initialized")

        # 2. Get SPY Spot
        spot_quotes = ctx.quote(["SPY.US"])
        if not spot_quotes:
            logger.error("Failed to fetch SPY spot price")
            return
        spot = float(spot_quotes[0].last_done)
        logger.info(f"Current SPY Spot: {spot}")

        # 3. Get 0DTE Exexpiry Date Object
        now = datetime.now(ZoneInfo("US/Eastern"))
        today_date = now.date() 
        logger.info(f"Targeting 0DTE Expiry: {today_date}")

        # 4. Get Full Chain Info
        chain_info = ctx.option_chain_info_by_date("SPY.US", today_date)
        if not chain_info:
            logger.error(f"No option chain info found for {today_date}")
            return
        
        logger.info(f"Found {len(chain_info)} strikes in total chain")

        # 5. Filter Window (+/- 70) and collect symbols
        window = 70.0
        min_strike = spot - window
        max_strike = spot + window
        
        research_symbols = []
        strike_map = {} # symbol -> strike

        for s in chain_info:
            # Longport SDK StrikePriceInfo uses 'price' instead of 'strike_price'
            strike = float(s.price) if hasattr(s, 'price') else 0.0
            if min_strike <= strike <= max_strike:
                if hasattr(s, 'call_symbol') and s.call_symbol:
                    research_symbols.append(s.call_symbol)
                    strike_map[s.call_symbol] = strike
                if hasattr(s, 'put_symbol') and s.put_symbol:
                    research_symbols.append(s.put_symbol)
                    strike_map[s.put_symbol] = strike

        logger.info(f"Filtering symbols in window [{min_strike}, {max_strike}]: {len(research_symbols)} contracts")

        # 6. Fetch Quotes in Batches (Longport Limits: ~100 symbols per sub or specific RPS)
        batch_size = 20 # Smaller batches
        all_quotes = []
        import time
        
        for i in range(0, len(research_symbols), batch_size):
            batch = research_symbols[i:i+batch_size]
            try:
                quotes = ctx.option_quote(batch)
                if quotes:
                    all_quotes.extend(quotes)
                logger.info(f"Fetched batch {i//batch_size + 1}: {len(batch)} symbols")
            except Exception as b_err:
                logger.warning(f"Batch {i} failed: {b_err}")
            
            # Rate limiting sleep
            time.sleep(1.5) 

        # 7. Aggregate Volume by Strike
        volume_dist = {} # strike -> {call_vol, put_vol, total_vol}
        
        for q in all_quotes:
            strike = strike_map.get(q.symbol)
            if strike is None: continue
            
            if strike not in volume_dist:
                volume_dist[strike] = {"call_vol": 0, "put_vol": 0, "total_vol": 0}
            
            vol = int(q.volume)
            # Classification based on Longport SDK attr
            is_call = False
            if hasattr(q, 'option_type'):
                is_call = "Call" in str(q.option_type)
            elif ".C." in q.symbol: # Fallback symbol parsing
                is_call = True
            
            if is_call:
                volume_dist[strike]["call_vol"] += vol
            else:
                volume_dist[strike]["put_vol"] += vol
            
            volume_dist[strike]["total_vol"] += vol

        # 8. Sort and Display Top 10 High Volume Strikes
        sorted_strikes = sorted(volume_dist.items(), key=lambda x: x[1]["total_vol"], reverse=True)
        
        print("\n" + "="*50)
        print(f"TOP 15 HIGH VOLUME STRIKES (Window: +/- {window})")
        print(f"Spot: {spot}")
        print("="*50)
        print(f"{'Strike':<10} | {'Total Vol':<12} | {'Call Vol':<10} | {'Put Vol':<10}")
        print("-"*50)
        
        for strike, data in sorted_strikes[:15]:
            print(f"{strike:<10.1f} | {data['total_vol']:<12,d} | {data['call_vol']:<10,d} | {data['put_vol']:<10,d}")
        
        # 9. Save to JSON for further analysis
        output_file = os.path.join(os.path.dirname(__file__), f"vol_dist_{today_date}.json")
        with open(output_file, "w") as f:
            # Convert float keys to string for JSON
            json_friendly = {str(k): v for k, v in volume_dist.items()}
            json.dump({
                "timestamp": now.isoformat(),
                "spot": spot,
                "window": window,
                "distribution": json_friendly
            }, f, indent=2)
        
        logger.info(f"Research results saved to {output_file}")

    except Exception as e:
        logger.error(f"Research script failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(research_volume_distribution())
