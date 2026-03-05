import asyncio
import json
import websockets
import time

WS_URL = "ws://localhost:8001/ws/dashboard"

async def monitor_deltas():
    print(f"Subscribing to {WS_URL}...")
    last_time = time.monotonic()
    try:
        async with websockets.connect(WS_URL) as ws:
            while True:
                msg = await ws.recv()
                now = time.monotonic()
                interval = now - last_time
                last_time = now
                
                data = json.loads(msg)
                mtype = data.get("type")
                
                # Highlight intervals > 1.2s or < 0.8s
                j_flag = " [!] JITTER" if interval > 1.5 or interval < 0.5 else ""
                print(f"[{mtype.upper()}] Interval: {interval:.3f}s{j_flag}")
                
                if mtype == "dashboard_delta":
                    changes = data.get("changes", {})
                    keys = list(changes.keys())
                    ui_state = changes.get("agent_g_ui_state", {})
                    ui_keys = list(ui_state.keys())
                    agent_g_data = changes.get("agent_g_data", {})
                    data_keys = list(agent_g_data.keys())
                    
                    print(f"[DELTA] Keys: {keys}")
                    if data_keys: print(f"  -> agent_g_data: {data_keys}")
                    if ui_keys: print(f"  -> agent_g_ui_state: {ui_keys}")
                    
                    if "depth_profile" in ui_keys:
                        dp = ui_state["depth_profile"]
                        first_strike = dp[0]["strike"] if dp else "N/A"
                        c_pct = dp[0]["call_pct"] if dp else 0.0
                        print(f"  -> Depth Profile Updated ({len(dp)} rows, first={first_strike}, c_pct={c_pct:.6f})")
                    else:
                        print("  -> [!] Depth Profile NOT in delta")
                
                elif mtype == "dashboard_init" or mtype == "dashboard_update":
                    print(f"[{mtype.upper()}] Full snapshot received.")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(monitor_deltas())
