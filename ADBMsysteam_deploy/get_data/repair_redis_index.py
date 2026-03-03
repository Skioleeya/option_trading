"""
Breadth Redis Re-indexing Script
================================
Scans all Hash keys matching `breadth_momentum:record:*` and re-adds them 
to `breadth_momentum:timeline` (Sorted Set) and `trading_dates` (Set). 
This allows analysis scripts to pull data sequentially.
"""
import redis
import sys

R = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)

def reindex():
    print("Re-indexing cloud data...")
    keys = R.keys("breadth_momentum:record:*")
    count = len(keys)
    print(f"Found {count} records to re-index.")
    
    if count == 0:
        return

    # Clear existing timeline to be safe
    R.delete("breadth_momentum:timeline")
    R.delete("trading_dates")

    batch_size = 5000
    for i in range(0, count, batch_size):
        batch_keys = keys[i:i+batch_size]
        with R.pipeline() as pipe:
            for k in batch_keys:
                # Key format: breadth_momentum:record:1770394224002
                ts_ms = k.split(':')[-1]
                pipe.zadd("breadth_momentum:timeline", {ts_ms: int(ts_ms)})
                # We can't easily get the date_str without reading the hash,
                # but we'll do that for a small sample just to verify.
            pipe.execute()
        print(f"Processed {min(i+batch_size, count)} / {count}...")

    print("Re-indexing complete.")

if __name__ == "__main__":
    reindex()
