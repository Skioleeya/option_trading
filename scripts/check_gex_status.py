"""Verification script for GexStatusBar data plumbing."""
import asyncio
import json
import websockets

WS_URL = "ws://localhost:8001/ws/dashboard"

async def check():
    print(f"[*] Connecting to {WS_URL}...")
    try:
        async with websockets.connect(WS_URL, open_timeout=5, ping_timeout=10) as ws:
            print("[+] Connected. Waiting for dashboard_init or dashboard_update...")
            for _ in range(30):
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                d = json.loads(msg)
                msg_type = d.get("type", "")
                
                if msg_type in ("dashboard_init", "dashboard_update"):
                    print(f"\nMessage type : {msg_type}")
                    
                    # 1. Root level checks
                    print("\n--- Root Level Fields ---")
                    fields = ["net_gex", "gamma_walls", "gamma_flip_level"]
                    for f in fields:
                        val = d.get(f, "MISSING")
                        print(f"{f:18}: {val}")
                    
                    # 2. agent_g.data level checks (legacy compatibility)
                    print("\n--- agent_g.data Level Fields ---")
                    data = d.get("agent_g", {}).get("data", {})
                    if not data:
                        print("[!] agent_g.data is empty!")
                    else:
                        for f in fields:
                            val = data.get(f, "MISSING")
                            print(f"{f:18}: {val}")
                            
                    return
                elif msg_type == "keepalive":
                    continue
            print("[!] Did not receive a full payload in 30 messages.")
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
