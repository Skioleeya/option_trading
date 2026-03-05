import asyncio
import redis.asyncio as redis
import os
import sys
from collections import defaultdict
from shared.config.persistence import PersistenceConfig

async def main():
    conf = PersistenceConfig()
    r = redis.Redis(host='localhost', port=conf.redis_port, db=conf.redis_db, decode_responses=True)
    
    print(f"Connected to Redis at {conf.redis_port}")
    
    # Let's count keys
    cursors = "0"
    all_keys = []
    
    while True:
        cursor, keys = await r.scan(cursor=cursors, match="*", count=5000)
        all_keys.extend(keys)
        cursors = cursor
        if cursors == 0 or cursors == "0":
            break
            
    print(f"Total keys in Redis: {len(all_keys)}")
    
    # Group keys by prefix
    prefixes = defaultdict(int)
    for k in all_keys:
        prefix = k.split(":")[0]
        prefixes[prefix] += 1
        
    for p, count in sorted(prefixes.items()):
        print(f"  {p}: {count}")
        
    print("\nLooking for exact options symbols...")
    opt_keys = [k for k in all_keys if 'SPY' in k and len(k) > 10]
    print(f"Found {len(opt_keys)} keys containing 'SPY'. Sample:")
    for k in opt_keys[:5]:
        print(f"  {k}")
        
    # Check feeds if there are tracking sets
    tracked = await r.smembers("l0:tracked_symbols")
    if tracked:
        print(f"\nFound 'l0:tracked_symbols' set with {len(tracked)} symbols.")
    else:
        print("\nSet 'l0:tracked_symbols' not found.")
        
    await r.aclose()

if __name__ == "__main__":
    asyncio.run(main())
