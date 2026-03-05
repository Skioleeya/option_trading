"""Test Depth Profile — GEX Distribution.

This script connects to the live backend WebSocket and extracts the 
calculated Depth Profile matrix, specifically focusing on the user-requested
strike window (678 - 691).

Usage:
    python scripts/test_depth_profile.py
"""

import asyncio
import json
import sys
from colorama import Fore, Style, init

init(autoreset=True)

WS_URL = "ws://localhost:8001/ws/dashboard"
STRIKE_MAX = 691.0
STRIKE_MIN = 678.0

async def dump_depth_profile():
    import websockets
    print(f"\n[*] Connecting to {WS_URL} to fetch Depth Profile...")
    
    try:
        async with websockets.connect(WS_URL, open_timeout=5) as ws:
            state = {}
            for _ in range(50):
                raw = await asyncio.wait_for(ws.recv(), timeout=15)
                msg = json.loads(raw)
                mtype = msg.get("type", "")
                
                if mtype in ("dashboard_init", "dashboard_update"):
                    state = msg
                    if state.get("agent_g", {}).get("data", {}).get("net_gex", 0) != 0:
                        break
                elif mtype == "dashboard_delta" and state:
                    changes = msg.get("changes", {})
                    ad = state.setdefault("agent_g", {}).setdefault("data", {})
                    ui = ad.setdefault("ui_state", {})
                    if "agent_g_ui_state" in changes:
                        ui.update(changes["agent_g_ui_state"])
                        
                    if ad.get("net_gex", 0) != 0:
                        break
                        
            if not state:
                print("[!] No state assembled.")
                return
                
            ad = state.get("agent_g", {}).get("data", {})
            ui = ad.get("ui_state", {})
            depth = ui.get("depth_profile", [])
            spot = state.get("spot", 0)
            
            print(f"\n{Fore.CYAN}=== DEPTH PROFILE (GEX) {STRIKE_MIN} -> {STRIKE_MAX} ==={Style.RESET_ALL}")
            print(f"Current SPY Spot: {spot}")
            if not depth:
                print(f"{Fore.RED}[!] Depth profile is empty!{Style.RESET_ALL}")
                return
                
            print(f"\n{'Strike':>8} | {'Call GEX %':>10} | {'Put GEX %':>10} | {'Net GEX':>12}")
            print("-" * 50)
            
            # Sort descending to match UI rendering (highest strike top)
            depth_sorted = sorted(depth, key=lambda x: x["strike"], reverse=True)
            
            found_in_range = False
            for row in depth_sorted:
                strike = row["strike"]
                if STRIKE_MIN <= strike <= STRIKE_MAX:
                    found_in_range = True
                    call_pct = row.get("call_pct", 0.0) * 100.0  # Presenter outputs [0, 1] ratios
                    put_pct = row.get("put_pct", 0.0) * 100.0
                    
                    strike_str = f"{strike:.1f}"
                    if abs(strike - spot) < 1.0:
                        strike_str = f"{Fore.YELLOW}{strike_str}{Style.RESET_ALL}"
                        
                    print(f"{strike_str:>17} | {call_pct:>9.1f}% | {put_pct:>9.1f}%")
                    
            if not found_in_range:
                print(f"{Fore.YELLOW}No strikes found in the [678, 691] range.{Style.RESET_ALL}")
                print("\nShowing top 5 available strikes for debugging:")
                for row in depth_sorted[:5]:
                     print(f"  {row['strike']}")
                     
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(dump_depth_profile())
