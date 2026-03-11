import redis
import json

def check_payload():
    r = redis.Redis(host='localhost', port=6380, db=0)
    data = r.lindex("spy:snapshots:latest", 0)
    if not data:
        print("No payload in Redis list 'spy:snapshots:latest'")
        return
        
    payload = json.loads(data)
    ui_state = payload.get("agent_g", {}).get("data", {}).get("ui_state", {})
    
    depth_profile = ui_state.get("depth_profile", [])
    macro_volume = ui_state.get("macro_volume_map", {})
    active_options = ui_state.get("active_options", [])
    
    # Check raw data
    agent_b_data = payload.get("agent_g", {}).get("data", {}).get("agent_b", {}).get("data", {})
    raw_strikes = agent_b_data.get("per_strike_gex", [])
    
    print(f"Payload total size: {len(data) / 1024:.2f} KB")
    print(f"Depth Profile (UI) rows: {len(depth_profile)}")
    print(f"Raw AgentB per_strike_gex: {len(raw_strikes)}")
    print(f"Macro Volume Map strikes: {len(macro_volume)}")
    print(f"Active Options count: {len(active_options)}")

if __name__ == "__main__":
    check_payload()
