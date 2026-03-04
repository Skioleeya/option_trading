"""Quick check: is 'atm' present at the payload root level?"""
import asyncio
import json
import sys
import websockets

WS_URL = "ws://localhost:8001/ws/dashboard"

async def check():
    print(f"[*] Connecting to {WS_URL}...")
    async with websockets.connect(WS_URL, open_timeout=5, ping_timeout=10) as ws:
        print("[+] Connected. Waiting for dashboard_init or dashboard_update...")
        for _ in range(30):
            msg = await asyncio.wait_for(ws.recv(), timeout=10)
            d = json.loads(msg)
            msg_type = d.get("type", "")
            if msg_type in ("dashboard_init", "dashboard_update"):
                atm = d.get("atm")
                print(f"\nMessage type : {msg_type}")
                print(f"atm at root  : {atm}")
                if atm is None:
                    print("\n[!] atm is NULL at payload root — backend may not have locked anchor yet.")
                    print("    Check backend logs for [AtmDecayTracker] ANCHOR LOCKED message.")
                    # Also show top-level keys for debugging
                    print(f"\nTop-level keys in payload: {list(d.keys())}")
                else:
                    print(f"\n[OK] ATM data found: strike={atm.get('strike')} locked_at={atm.get('locked_at')}")
                    print(f"     call_pct={atm.get('call_pct'):.4f}  put_pct={atm.get('put_pct'):.4f}  straddle_pct={atm.get('straddle_pct'):.4f}")
                return
            elif msg_type == "keepalive":
                continue
        print("[!] Did not receive a full payload in 30 messages.")

if __name__ == "__main__":
    asyncio.run(check())
