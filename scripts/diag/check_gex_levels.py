import redis
import json
import sys
from datetime import datetime

def check_gex():
    r = redis.Redis(host='localhost', port=6379, db=0)
    # Try to find the latest L3 payload or L1 snapshot
    # Typical key: app:latest_payload or from the timeseries
    key = "app:latest_payload"
    raw = r.get(key)
    if not raw:
        print("Error: Could not find 'app:latest_payload' in Redis.")
        return

    payload = json.loads(raw)
    per_strike = payload.get("ui_state", {}).get("depth_profile", [])
    if not per_strike:
        # Fallback to internal decision data if depth_profile is empty
        per_strike = payload.get("per_strike_gex", [])

    print(f"--- GEX Analysis (Strikes 674 to 687) ---")
    print(f"Time: {payload.get('data_timestamp', 'N/A')}")
    print(f"Spot: {payload.get('spot', 'N/A')}")
    print(f"{'Strike':<10} | {'GEX Notional':<15} | {'Call Pct':<10} | {'Put Pct':<10}")
    print("-" * 55)

    # Note: DepthProfileRow entries often use 'strike', 'c_pct', 'p_pct'
    # or just raw GEX if we are looking at the pre-calculated aggregates.
    
    found = False
    for row in per_strike:
        strike = row.get("strike", 0)
        if 674 <= strike <= 687:
            found = True
            # The UI depth profile uses percentages/normalized values.
            # Let's see what's actually in the row.
            c_pct = row.get("call_pct", row.get("c_pct", 0))
            p_pct = row.get("put_pct", row.get("p_pct", 0))
            # If we want raw GEX, we need the L1 aggregates
            print(f"{strike:<10} | {'N/A':<15} | {c_pct:<10.4f} | {p_pct:<10.4f}")

    if not found:
        print("No strikes found in range 674-687 in current payload.")
        # Dump keys to see what's available
        print("\nAvailable row keys:", per_strike[0].keys() if per_strike else "N/A")

if __name__ == "__main__":
    check_gex()
