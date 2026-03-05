import asyncio
import json
import websockets
import sys

WS_URL = "ws://localhost:8001/ws/dashboard"

async def debug_depth_profile():
    print(f"Connecting to {WS_URL}...")
    try:
        async with websockets.connect(WS_URL) as ws:
            print("Connected. Waiting for payload...")
            for _ in range(5):
                msg = await ws.recv()
                data = json.loads(msg)
                
                if data.get("type") in ["dashboard_init", "dashboard_update"]:
                    ui_state = data.get("agent_g", {}).get("data", {}).get("ui_state", {})
                    profile = ui_state.get("depth_profile", [])
                    
                    if profile:
                        print("\n" + "="*80)
                        print(f"{'Strike':<10} | {'Call %':<10} | {'Put %':<10} | {'ATM':<5} | {'Flip':<5}")
                        print("-" * 80)
                        for row in profile:
                            strike = row.get("strike", 0.0)
                            c_pct = row.get("call_pct", 0.0)
                            p_pct = row.get("put_pct", 0.0)
                            is_atm = row.get("is_atm", False) or row.get("is_spot", False)
                            is_flip = row.get("is_flip", False)
                            
                            atm_mark = "*" if is_atm else ""
                            flip_mark = "F" if is_flip else ""
                            
                            print(f"{strike:<10.2f} | {c_pct:<10.4f} | {p_pct:<10.4f} | {atm_mark:<5} | {flip_mark:<5}")
                        print("="*80)
                        break
                elif data.get("type") == "keepalive":
                    print(".", end="", flush=True)
                else:
                    print(f"Skipping {data.get('type')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_depth_profile())
