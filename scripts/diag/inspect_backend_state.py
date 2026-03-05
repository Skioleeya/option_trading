import asyncio
import os
import sys

sys.path.append(os.getcwd())

from l0_ingest.feeds.option_chain_builder import OptionChainBuilder

async def inspect_store():
    print("Initializing OptionChainBuilder (minimal)...")
    ocb = OptionChainBuilder()
    # We can't easily start the whole gateway without credentials, 
    # but we can try to look at the SubscriptionManager or settings.
    
    from shared.config import settings
    print(f"Subscription Max: {settings.subscription_max}")
    print(f"Enable Tier 2: {settings.enable_tier2_polling}")
    
    # Let's try to see if we can get the active symbols from a running process?
    # No, we'll just check the code again or run a script that connects to the 
    # health/diagnostic endpoint if it exists.
    
    import requests
    try:
        resp = requests.get("http://localhost:8001/health")
        print(f"Backend Health: {resp.json()}")
    except:
        print("Backend not reachable via HTTP.")

if __name__ == "__main__":
    asyncio.run(inspect_store())
