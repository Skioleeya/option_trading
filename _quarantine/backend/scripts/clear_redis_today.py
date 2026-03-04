import asyncio
import redis.asyncio as redis
from datetime import datetime

async def clear_todays_data():
    today_str = datetime.now().strftime("%Y%m%d")
    print(f"Targeting data for: {today_str}")
    
    r = redis.from_url("redis://localhost:6380/0")
    
    # Find keys with today's date
    keys_to_delete = []
    async for key in r.scan_iter(f"*{today_str}*"):
        keys_to_delete.append(key.decode('utf-8'))
        
    # Also clear the latest snapshots list to reset the sliding window
    keys_to_delete.append("spy:snapshots:latest")
    
    if not keys_to_delete:
        print("No keys found to delete.")
    else:
        print(f"Found keys to delete: {keys_to_delete}")
        # Delete the keys
        await r.delete(*keys_to_delete)
        print("Successfully deleted keys.")
        
    await r.aclose()

if __name__ == "__main__":
    asyncio.run(clear_todays_data())
