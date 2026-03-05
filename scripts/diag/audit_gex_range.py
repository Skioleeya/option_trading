
import asyncio
import json
import logging
import numpy as np
import redis
from datetime import datetime
from l1_compute.analysis.bsm_fast import compute_greeks_batch
from l1_compute.analysis.bsm import get_trading_time_to_maturity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gex_audit")

async def audit_gex():
    # 1. Connect to Redis
    r = redis.Redis(host='127.0.0.1', port=6380, db=0)
    
    # 2. Get latest snapshot to find Spot and IVs
    latest_raw = r.lrange("spy:snapshots:latest", 0, 0)
    if not latest_raw:
        print("No snapshots found in Redis.")
        return
        
    payload = json.loads(latest_raw[0])
    spot = payload.get("spot", 0.0)
    print(f"Current Spot: {spot}")
    
    # 3. Define strike range
    strikes_to_check = [float(s) for s in range(674, 688)]
    
    # 4. We need the current IV and OI for these strikes
    # Since we can't easily get IV per strike from the L3 payload, 
    # we'll try to find any recent L1 data or just assume a flat IV for approximation if needed,
    # BUT, we can actually fetch the live chain if we import OptionChainBuilder.
    
    from app.container import build_container
    ctr = build_container()
    await ctr.option_chain_builder.initialize()
    
    print(f"Fetching live chain snapshot... Spot: {spot}")
    
    # Wait for hydration
    chain = []
    for i in range(30):
        snapshot = await ctr.option_chain_builder.fetch_chain()
        chain = snapshot.get("chain", [])
        if chain:
            break
        if i % 5 == 0:
            print(f"Waiting for chain hydration... ({i}s)")
        await asyncio.sleep(1)
        
    if not chain:
        print("Chain is still empty after 30s.")
        return
        
    available_strikes = sorted(list(set([opt['strike'] for opt in chain])))
    print(f"Available strikes: {min(available_strikes)} to {max(available_strikes)} (Count: {len(available_strikes)})")

    # Filter for target strikes
    target_chain = [opt for opt in chain if 674 <= opt['strike'] <= 687]
    
    if not target_chain:
        print("No options found in the chain for the target range.")
        return
        
    # Prepare batch compute arrays
    n = len(target_chain)
    spots = np.full(n, spot)
    strikes = np.array([opt['strike'] for opt in target_chain])
    ivs = np.array([opt.get('implied_volatility', 0.20) for opt in target_chain])
    is_call = np.array([opt['type'] == 'CALL' for opt in target_chain])
    ois = np.array([opt.get('open_interest', 0) for opt in target_chain])
    mults = np.full(n, 100.0)
    
    t_years = get_trading_time_to_maturity(datetime.now())
    
    # 5. Compute Greeks
    greeks, agg = compute_greeks_batch(spots, strikes, ivs, t_years, is_call, ois=ois, mults=mults)
    
    # 6. Calculate per-strike GEX in Billions
    # GEX = Gamma * OI * Spot^2 * 100 * 0.01
    gamma = greeks['gamma']
    gex_notional = gamma * ois * (spots**2) * mults * 0.01 / 1_000_000_000.0  # Billions
    
    print("\n" + "="*60)
    print(f"{'Strike':<8} | {'Type':<5} | {'OI':<10} | {'IV':<8} | {'GEX (B)':<10}")
    print("-" * 60)
    
    results = []
    for i in range(n):
        res = {
            "strike": strikes[i],
            "type": "CALL" if is_call[i] else "PUT",
            "oi": ois[i],
            "iv": ivs[i],
            "gex_b": gex_notional[i]
        }
        results.append(res)
        print(f"{res['strike']:<8.1f} | {res['type']:<5} | {res['oi']:<10} | {res['iv']:<8.2%} | {res['gex_b']:<10.2f}B")
    
    print("="*60)
    
    # 7. Summary
    total_gex = sum(gex_notional)
    print(f"Total GEX in Range 674-687: {total_gex:.2f}B")
    
    await ctr.option_chain_builder.shutdown()

if __name__ == "__main__":
    asyncio.run(audit_gex())
