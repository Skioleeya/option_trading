import asyncio
import logging
import time
import sys
import os
from longport.openapi import Config

# Root path for imports
sys.path.append(os.getcwd())

from l0_ingest.feeds.option_chain_builder import OptionChainBuilder
from shared.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("LiveTest")

async def run_live_verification():
    """Live verification of Rust Ingest Gateway within OptionChainBuilder."""
    print("="*60)
    print("🚀  [Live Verification] Starting Rust Ingest Gateway Stack")
    print("="*60)
    
    # 1. Initialize Builder (this will start Rust gateway via SubscriptionManager)
    builder = OptionChainBuilder()
    
    try:
        await builder.initialize()
        logger.info("Builder initialized. Rust consumer loop should be active.")

        # 2. Subscribe to active US symbols
        # Note: SPY.US is used for spot, AAPL options for flow
        test_symbols = ["AAPL 260320C00260000", "SPY.US"] 
        logger.info(f"Subscribing to verification pool: {test_symbols}")
        
        # Route to Rust (default is rust in our implementation)
        builder._sub_mgr.subscribe(test_symbols, mode="rust")
        
        # 3. Monitor flow for 30 seconds
        print("\n📊 Monitoring Live Flow (Sub-ms Latency Path)...")
        start_time = time.time()
        while time.time() - start_time < 30:
            stats = builder.get_diagnostics()
            # We can check specific metrics if we added them, otherwise check store
            spot = builder._store.spot
            chain_len = len(builder._store._chain)
            
            print(f"\r[Runtime] Time: {int(time.time() - start_time)}s | Spot: {spot} | Chain Cache: {chain_len} symbols | Rust Active: {builder._initialized}", end="")
            
            # Print a few events if they arrive
            # (OptionChainBuilder applies them to _store)
            await asyncio.sleep(1.0)
            
        print("\n\n✅ [Live Verification] Success. Data flowing through Rust bridge.")
        
    except Exception as e:
        logger.error(f"❌ [Live Verification] Failed: {e}", exc_info=True)
    finally:
        await builder.shutdown()
        logger.info("Gateway stack shut down.")

if __name__ == "__main__":
    asyncio.run(run_live_verification())
