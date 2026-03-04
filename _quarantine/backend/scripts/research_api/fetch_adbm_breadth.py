import os
import sys
import redis
import json
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Path to ADBM local environment
ADBM_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ADBMsysteam_deploy'))
ENV_PATH = os.path.join(ADBM_DIR, 'environment.env')

# Load ADBM environment
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

# Redis Configuration (matching ADBM defaults if not in env)
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

ET = ZoneInfo("America/New_York")

def get_breadth_data():
    """Fetch live and recent breadth data from Redis."""
    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True
        )
        
        print(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
        
        # 1. Fetch Latest Data from Timeline
        timeline_key = "breadth_momentum:timeline"
        latest_record_ids = r.zrevrange(timeline_key, 0, 0)
        
        if latest_record_ids:
            record_id = latest_record_ids[0]
            record_key = f"breadth_momentum:record:{record_id}"
            live_item = r.hgetall(record_key)
            if live_item:
                print("\n--- [LATEST BREADTH DATA] ---")
                print(f"Timestamp: {live_item.get('timestamp')}")
                print(f"BM (Momentum): {live_item.get('BM')}")
                print(f"Advancers: {live_item.get('advancers')}")
                print(f"Decliners: {live_item.get('decliners')}")
                print(f"Net Breadth: {live_item.get('net_breadth')}")
                print(f"Regime: {live_item.get('regime')}")
            else:
                print(f"\n[WARN] Record data missing for ID: {record_id}")
        else:
            print(f"\n[WARN] No data found in timeline: {timeline_key}")

        # 2. Fetch Recent Series Data (Last 5)
        recent_record_ids = r.zrevrange(timeline_key, 1, 5)
        
        if recent_record_ids:
            print(f"\n--- [RECENT SERIES DATA] ---")
            for rid in recent_record_ids:
                item = r.hgetall(f"breadth_momentum:record:{rid}")
                if item:
                    print(f"[{item.get('timestamp')}] BM: {item.get('BM')}, Nets: {item.get('net_breadth')}")
        else:
            print(f"\n[WARN] No historical series data found.")

    except Exception as e:
        print(f"\n[ERROR] Failed to fetch data from Redis: {e}")

if __name__ == "__main__":
    get_breadth_data()
