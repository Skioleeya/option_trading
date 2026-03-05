
import asyncio
import json
import websockets
import math
import numpy as np

async def validate_gex():
    url = "ws://localhost:8001/ws/dashboard"
    print(f"Connecting to {url}...")
    
    try:
        async with websockets.connect(url) as ws:
            # 1. Wait for a message with agent_g data
            found = False
            while not found:
                msg = await ws.recv()
                data = json.loads(msg)
                
                # Check for agent_g and depth_profile
                agent_g = data.get("agent_g", {})
                inner_data = agent_g.get("data", {})
                if not inner_data: continue
                
                net_gex_m = inner_data.get("net_gex", 0.0) # In Millions
                ui_state = inner_data.get("ui_state", {})
                depth_profile = ui_state.get("depth_profile", [])
                
                if not depth_profile:
                    print("Waiting for depth profile data...")
                    continue
                
                found = True
                print(f"Captured Snapshot. Net GEX: {net_gex_m/1000:.2f}B, Strikes: {len(depth_profile)}")
                
                # 2. Reverse Power-Law Scaling
                # final_pct = lin_pct ^ 0.4  => lin_pct = final_pct ^ (1/0.4) = final_pct ^ 2.5
                P_INDEX = 0.4
                REVERSE_P = 1.0 / P_INDEX
                
                lin_calls = []
                lin_puts = []
                strikes = []
                
                for row in depth_profile:
                    s = row['strike']
                    cp = row['call_pct']
                    pp = row['put_pct']
                    
                    l_c = math.pow(cp, REVERSE_P) if cp > 0 else 0.0
                    l_p = math.pow(pp, REVERSE_P) if pp > 0 else 0.0
                    
                    lin_calls.append(l_c)
                    lin_puts.append(l_p)
                    strikes.append(s)
                
                # 3. Calculate Scale Factor
                # net_gex = scale * (sum(lin_calls) - sum(lin_puts))
                # Note: net_gex sign: call is positive, put is technically positive in the list but negative in net.
                # In L3 presenter: lin_put_pct = abs(put_gex) / norm_max
                # So net_gex_m = norm_max * (sum(lin_calls) - sum(lin_puts))
                diff_sum = sum(lin_calls) - sum(lin_puts)
                if abs(diff_sum) < 1e-6:
                    print("Sum of linear percentages is near zero. Cannot scale.")
                    return
                
                norm_max = net_gex_m / diff_sum
                print(f"Calculated norm_max: {norm_max:.2f}M")
                
                # 4. Extract target range 674-687
                print("\n" + "="*50)
                print(f"{'Strike':<8} | {'Call GEX (M)':<15} | {'Put GEX (M)':<15} | {'Net (M)':<10}")
                print("-" * 50)
                
                range_gex = 0.0
                for i in range(len(strikes)):
                    s = strikes[i]
                    if 674 <= s <= 687:
                        c_m = lin_calls[i] * norm_max
                        p_m = lin_puts[i] * norm_max
                        net_m = c_m - p_m
                        range_gex += net_m
                        print(f"{s:<8.1f} | {c_m:<15.2f} | {p_m:<15.2f} | {net_m:<10.2f}")
                
                print("=" * 50)
                print(f"Total range GEX (674-687): {range_gex/1000:.2f}B")
                
                # 5. Validation Check
                # 2026 Institutional Benchmark for SPY 0DTE:
                # - High Liquid Range (ATM +/- 2%): 5B-20B peak GEX per strike is normal.
                # - Total GEX 100B-200B is standard for a non-volatile day.
                # - GEX < 1B in this range might indicate a liquidity gap.
                
                is_normal = 50.0 <= abs(net_gex_m/1000) <= 300.0
                print(f"\nNet GEX Level ({net_gex_m/1000:.2f}B): {'NORMAL' if is_normal else 'ANOMALOUS'}")
                
                avg_abs_strike = np.mean([abs(lin_calls[i] - lin_puts[i]) * abs(norm_max) for i in range(len(strikes)) if 674 <= strikes[i] <= 687])
                print(f"Average Strike Intensity in Range: {avg_abs_strike:.2f}M")
                
                return
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(validate_gex())
