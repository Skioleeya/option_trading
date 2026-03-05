import asyncio
import json
import websockets
import time
import sys

WS_URL = "ws://localhost:8001/ws/dashboard"

async def check_gex_range():
    print(f"Connecting to {WS_URL} to capture GEX distribution (674-687)...")
    try:
        async with websockets.connect(WS_URL) as ws:
            count = 0
            while count < 3:  # Capture 3 samples
                msg = await ws.recv()
                data = json.loads(msg)
                mtype = data.get("type")
                
                # We need a full snapshot or a delta that contains depth_profile
                per_strike = []
                if mtype in ("dashboard_init", "dashboard_update"):
                    per_strike = data.get("payload", {}).get("ui_state", {}).get("depth_profile", [])
                    print(f"[{mtype.upper()}] Captured full snapshot.")
                elif mtype == "dashboard_delta":
                    changes = data.get("changes", {})
                    per_strike = changes.get("agent_g_ui_state", {}).get("depth_profile", [])
                    if per_strike:
                        print(f"[{mtype.upper()}] Captured delta with depth_profile.")
                
                if per_strike:
                    print(f"\n--- GEX Sample {count+1} ---")
                    print(f"{'Strike':<10} | {'Call Pct':<10} | {'Put Pct':<10}")
                    print("-" * 35)
                    found = False
                    for row in per_strike:
                        strike = row.get("strike", 0)
                        if 674 <= strike <= 687:
                            found = True
                            c_pct = row.get("call_pct", 0)
                            p_pct = row.get("put_pct", 0)
                            print(f"{strike:<10} | {c_pct:<10.4f} | {p_pct:<10.4f}")
                    if not found:
                        print("Range 674-687 not found in this sample.")
                    count += 1
                
                if count >= 3:
                    break
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_gex_range())
