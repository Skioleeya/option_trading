import asyncio
import json
import sys
import websockets
import jsonpatch
from colorama import Fore, Style, init

init(autoreset=True)

WS_URL = "ws://localhost:8001/ws/dashboard"

async def test_l0_l4_pipeline():
    print(f"{Fore.CYAN}[*] Connecting to L4 WebSocket Endpoint at {WS_URL}...{Style.RESET_ALL}")
    
    try:
        async with websockets.connect(WS_URL, open_timeout=5, ping_timeout=10) as websocket:
            print(f"{Fore.GREEN}[+] Connection Established! Waiting for incoming L0-L4 Payload...{Style.RESET_ALL}")
            # Wait for a full payload (skip init if necessary)
            print(f"{Fore.YELLOW}[*] Waiting for a fully enriched payload (applying custom L3 deltas)...{Style.RESET_ALL}")
            current_state = None
            data = None
            message = ""
            for _ in range(50): # Try up to 50 incoming messages
                message = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                d = json.loads(message)
                
                if d.get("type") in ["dashboard_init", "dashboard_update"] and "agent_g" in d:
                    current_state = d
                elif d.get("type") == "dashboard_delta" and current_state is not None:
                    try:
                        changes = d.get("changes", {})
                        if "agent_g_ui_state" in changes:
                            ui_state = current_state.setdefault("agent_g", {}).setdefault("data", {}).setdefault("ui_state", {})
                            ui_state.update(changes["agent_g_ui_state"])
                        if "signal" in changes:
                            signal_data = current_state.setdefault("agent_g", {}).setdefault("data", {})
                            signal_data.update(changes["signal"])
                        for k, v in changes.items():
                            if k not in ("agent_g_ui_state", "signal"):
                                current_state[k] = v
                    except Exception as e:
                        print(f"    [Trace] Patch Error: {e}")
                elif d.get("type") == "keepalive":
                    continue
                else:
                    print(f"    [Trace] Initializing state or skipping unknown type: {d.get('type')}")
                    continue
                    
                if current_state:
                    agent_test = current_state.get("agent_g", {}).get("data", {})
                    ui_test = agent_test.get("ui_state", {})
                    walls = ui_test.get("wall_migration", [])
                    print(f"    [Trace] wall_migration = {walls}")
                    if len(walls) > 0 and any("label" in w for w in walls):
                        data = current_state
                        break
                    else:
                        print(f"    [Trace] State tracked, but L3 Walls still empty or lacked label. Applying next delta...")
            
            if data is None:
                print(f"{Fore.RED}[!] Could not find a full L1/L2 payload after 50 messages.{Style.RESET_ALL}")
                try:
                    data = json.loads(message) # fallback to last
                except:
                    return
            
            print(f"\n{Fore.YELLOW}=== L0-L4 PIPELINE INTEGRITY REPORT ==={Style.RESET_ALL}")
            print(f"Payload Size (Bytes) : {len(message):,}")
            print(f"Message Type         : {data.get('type', 'Unknown')}")
            
            # Phase 1: Verify L0 (Ingestion Data)
            print(f"\n{Fore.CYAN}--- L0 (Ingest / Feed) Verification ---{Style.RESET_ALL}")
            spot = data.get("spot")
            timestamp = data.get("data_timestamp")
            if spot and float(spot) > 0:
                print(f"✅ Market Spot Price : {spot}")
            else:
                print(f"❌ Missing or Invalid Spot Price")
            
            if timestamp:
                print(f"✅ Snapshot Timestamp: {timestamp}")
            else:
                print(f"❌ Missing Timestamp")
                
            agent_data = data.get("agent_g", {}).get("data", {})
            ui_state = agent_data.get("ui_state", {})
                
            # Phase 2: Verify L1 (Compute / GPU / Greeks)
            print(f"\n{Fore.CYAN}--- L1 (Compute / GPU / Greeks) Verification ---{Style.RESET_ALL}")
            micro = ui_state.get("micro_stats", {})
            net_gex = micro.get("net_gex", {}).get("label")
            vanna = micro.get("vanna", {}).get("label")
            if net_gex and net_gex != "—":
                print(f"✅ Net GEX          : {net_gex}")
                print(f"✅ Vanna Flow       : {vanna}")
            else:
                print(f"❌ Missing L1 Compute Aggregations (GEX UI unpopulated)")
                
            # Phase 3: Verify L2 (Decision / Agent Analysis)
            print(f"\n{Fore.CYAN}--- L2 (Decision / Agents) Verification ---{Style.RESET_ALL}")
            direction = agent_data.get("direction")
            confidence = agent_data.get("confidence")
            
            if direction and confidence is not None:
                print(f"✅ Master Direction : {direction}")
                print(f"✅ Agent Confidence : {confidence * 100:.1f}%")
            else:
                print(f"❌ Missing L2 Agent Decisions")
                
            # Phase 4: Verify L3 (Assembly / UI State Hub)
            print(f"\n{Fore.CYAN}--- L3 (Assembly / UI State Hub) Verification ---{Style.RESET_ALL}")
            walls = ui_state.get("wall_migration", [])
            if isinstance(walls, list) and len(walls) > 0:
                call_wall = next((w for w in walls if "CALL" in w["label"]), None)
                put_wall = next((w for w in walls if "PUT" in w["label"]), None)
                print(f"✅ Call Wall Struct : Identified (Strike: {call_wall.get('strike') if call_wall else 'N/A'})")
                print(f"✅ Put Wall Struct  : Identified (Strike: {put_wall.get('strike') if put_wall else 'N/A'})")
            else:
                print(f"❌ Missing L3 Assembled UI Tracks (None found in wall_migration array)")
                
            depth = ui_state.get("depth_profile", [])
            print(f"\n{Fore.CYAN}--- IV & DEPTH PROFILE ---{Style.RESET_ALL}")
            print(f"Depth Profile Size: {len(depth)}")
            if (len(depth) > 0):
                print(f"First profile row: {depth[0]}")
            iv_val = data.get("spy_atm_iv", "NOT_FOUND")
            print(f"spy_atm_iv from agent_g data: {iv_val}")
            print(f"spy_atm_iv from agent_g data: {agent_data.get('spy_atm_iv', 'NOT_FOUND')}")

            print(f"\n{Fore.GREEN}[*] Analysis Complete! Terminating connection.{Style.RESET_ALL}")

    except websockets.exceptions.ConnectionClosed:
        print(f"{Fore.RED}[!] WebSocket connection closed unexpectedly.{Style.RESET_ALL}")
    except asyncio.TimeoutError:
        print(f"{Fore.RED}[!] Timeout waiting for payload. Is the market closed or data feed dead?{Style.RESET_ALL}")
    except ConnectionRefusedError:
        print(f"{Fore.RED}[!] Connection refused. Is the Uvicorn backend running?{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[!] Unexpected Error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(test_l0_l4_pipeline())
