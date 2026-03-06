import asyncio
import json
import redis.asyncio as redis
from datetime import datetime
from zoneinfo import ZoneInfo

async def check_redis():
    client = redis.Redis(host='127.0.0.1', port=6380, decode_responses=True)
    today = datetime.now(ZoneInfo("US/Eastern")).strftime("%Y%m%d")
    
    series_key = f"app:atm_decay_series:{today}"
    anchor_key = f"app:opening_atm:{today}"
    
    print(f"Checking keys for {today}...")
    
    anchor_raw = await client.get(anchor_key)
    print(f"Anchor key ({anchor_key}): {'FOUND' if anchor_raw else 'MISSING'}")
    if anchor_raw:
        print(f"  Value: {anchor_raw[:100]}...")
        
    series_len = await client.llen(series_key)
    print(f"Series key ({series_key}): {'FOUND' if series_len > 0 else 'EMPTY/MISSING'} (Length: {series_len})")
    
    print("Scanning all keys...")
    all_keys = await client.keys("*")
    print(f"Total keys: {len(all_keys)}")
    for k in all_keys[:20]:
        print(f"  - {k}")
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(check_redis())
