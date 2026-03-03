
import asyncio
from redis.asyncio import Redis
import json

async def check_redis():
    client = Redis(host="127.0.0.1", port=6380, decode_responses=True)
    try:
        print("--- Redis Persistence Diagnostic ---")
        
        # 1. Check Snapshot list
        snapshots_len = await client.llen("spy:snapshots:latest")
        print(f"[Snapshots] Key 'spy:snapshots:latest' length: {snapshots_len}")
        
        # 2. Check ATM Anchor
        import datetime
        today = datetime.datetime.now().strftime("%Y%m%d")
        anchor_key = f"app:opening_atm:{today}"
        anchor_data = await client.get(anchor_key)
        print(f"[ATM Anchor] Key '{anchor_key}': {'FOUND' if anchor_data else 'MISSING'}")
        
        # 3. Check ATM Series
        series_key = f"app:atm_decay_series:{today}"
        series_len = await client.llen(series_key)
        print(f"[ATM Series] Key '{series_key}' length: {series_len}")
        
        # 4. Check for binary flags (Persistence config)
        info = await client.info("persistence")
        print(f"[Persistence Info] rdb_last_save_time: {info.get('rdb_last_save_time')}")
        print(f"[Persistence Info] aof_enabled: {info.get('aof_enabled')}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(check_redis())
