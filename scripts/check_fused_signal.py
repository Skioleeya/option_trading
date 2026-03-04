"""Verify fused_signal appears in agent_g.data block of the WebSocket payload."""
import asyncio, json, websockets

WS_URL = "ws://localhost:8001/ws/dashboard"

async def check():
    print(f"[*] Connecting to {WS_URL}...")
    async with websockets.connect(WS_URL, open_timeout=8, ping_timeout=10) as ws:
        print("[+] Connected. Waiting for a full payload...")
        for _ in range(30):
            msg = await asyncio.wait_for(ws.recv(), timeout=12)
            d = json.loads(msg)
            if d.get("type") in ("dashboard_init", "dashboard_update"):
                data = d.get("agent_g", {}).get("data", {})
                ui_state = data.get("ui_state", {})
                skew = ui_state.get("skew_dynamics")
                print(f"\nMessage type : {d['type']}")
                print(f"\n--- skew_dynamics at agent_g.data.ui_state.skew_dynamics ---")
                if skew is None:
                    print("skew_dynamics is MISSING or None")
                else:
                    print(json.dumps(skew, indent=2))
                return
asyncio.run(check())
