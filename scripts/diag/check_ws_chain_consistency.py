import asyncio
import websockets
import json

async def check_ws():
    uri = "ws://localhost:8001/ws/dashboard"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected. Waiting for payload...")
            for _ in range(10):
                msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(msg)
                
                # Use same logic as v3_gex_validator
                agent_g = data.get("agent_g", {})
                inner_data = agent_g.get("data", {})
                if not inner_data: continue
                
                ui_state = inner_data.get("ui_state", {})
                depth_profile = ui_state.get("depth_profile", [])
                
                if not depth_profile:
                    print("Waiting for depth profile data...")
                    continue
                    
                print(f"\n[PAYLOAD RECEIEVD]")
                
                strike_prices = [s.get("strike") for s in depth_profile if s.get("strike") is not None]
                if not strike_prices:
                    print("Failed to parse strike prices.")
                    continue
                    
                min_strike, max_strike = min(strike_prices), max(strike_prices)
                
                spot = ui_state.get("micro_stats", {}).get("spot_price", 0)
                if not spot:
                    # Let's try to get spot elsewhere if it's missing in micro_stats
                    print("Spot not in ui_state.micro_stats")
                    spot = inner_data.get("spot_price", 0) # Fallback
                
                print("-" * 50)
                print(f"Active Strikes Computed: {len(strike_prices)}")
                print(f"Total Monitored Options (Calls + Puts): {len(strike_prices) * 2}")
                print(f"Range: {min_strike} -> {max_strike}")
                print(f"Spot Price: {spot}")
                if spot:
                     print(f"Window bounds: Call +{max_strike - spot:.2f} / Put {min_strike - spot:.2f}")
                print("-" * 50)
                
                return
                    
    except Exception as e:
         print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_ws())
