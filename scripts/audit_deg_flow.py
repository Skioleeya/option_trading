"""DEG-FLOW Institutional Audit Harness (Phase 20).

Validates the mathematical correctness and consistency of Method D/E/G flows.
Usage: python scripts/audit_deg_flow.py
"""

import asyncio
import logging
import math
import os
import sys
from typing import Any

# Load environment variables from backend/.env
from dotenv import load_dotenv
load_dotenv("backend/.env")

# Set PYTHONPATH to include backend/app
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.models.flow_engine import FlowEngineInput
from app.services.flow import DEGComposer, FlowEngineD, FlowEngineE, FlowEngineG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DEG-Audit")

async def run_audit():
    logger.info("=== STARTING DEG-FLOW INSTITUTIONAL AUDIT ===")
    
    # 1. Mock Data Construction (Institutional Benchmark)
    # SPY 600 Call, Spot 590, IV 20%, HV 15%, Delta 0.4, Gamma 0.05, Vanna 0.1
    benchmark_input = FlowEngineInput(
        symbol="SPY_BENCHMARK",
        option_type="CALL",
        strike=600.0,
        spot=590.0,
        volume=1000,
        turnover=5000000.0,
        last_price=5.0,
        implied_volatility=0.20,
        historical_volatility=0.15,
        open_interest=5000,
        delta=0.4,
        gamma=0.05,
        vanna=0.1,
        atm_iv=0.18
    )
    
    inputs = [benchmark_input]
    
    # --- PHASE 13: FlowEngineD Audit ---
    logger.info("[Step 1] Auditing FlowEngineD (Gamma Imbalance)...")
    d_engine = FlowEngineD()
    d_res = d_engine.compute(inputs)[0]
    # Expected: 1000 * 0.05 * (590^2) * 100 * 0.01 * 1 = 17,405,000
    expected_d = 1000 * 0.05 * (590**2) * 100 * 0.01
    assert abs(d_res.flow_value - expected_d) < 1, f"D mismatch: {d_res.flow_value} vs {expected_d}"
    logger.info(f"  [PASS] Method D: {d_res.flow_value:,.2f}")

    # --- PHASE 14: FlowEngineE Audit ---
    logger.info("[Step 2] Auditing FlowEngineE (Vanna * dIV)...")
    e_engine = FlowEngineE()
    e_res = e_engine.compute(inputs)[0]
    # Expected: 1000 * 100 * |0.1| * (0.20 - 0.15) * sign(0.05 * Type) = 500.0
    expected_e = 1000 * 100 * 0.1 * 0.05
    assert abs(e_res.flow_value - expected_e) < 0.01, f"E mismatch: {e_res.flow_value} vs {expected_e}"
    logger.info(f"  [PASS] Method E: {e_res.flow_value:,.2f}")

    # --- PHASE 22: Persistent OI Audit ---
    logger.info("[Step 3] Auditing PersistentOIStore...")
    from app.services.system.persistent_oi_store import PersistentOIStore
    store = PersistentOIStore()
    date_str = "20260227"
    store.save_baseline(date_str, [{"symbol": "TEST_C", "open_interest": 1234}])
    baseline = store.get_baseline(date_str)
    assert baseline.get("TEST_C") == 1234
    logger.info("  [PASS] PersistentOIStore logic verified")

    # --- PHASE 15: FlowEngineG Audit (Persistence fallback) ---
    logger.info("[Step 4] Auditing FlowEngineG Fallback...")
    g_engine = FlowEngineG()
    g_results = await g_engine.compute(inputs, redis=None)
    assert g_results[0].flow_value == 0
    assert g_results[0].failure_reason == "redis_unavailable"
    logger.info("  [PASS] Method G Degraded Correctly")

    # --- PHASE 16: DEGComposer Audit ---
    logger.info("[Step 4] Auditing DEGComposer (Z-Score + Weighting)...")
    composer = DEGComposer()
    
    # Mock multiple inputs to get non-zero Z-Score std
    inps = [
        benchmark_input,
        benchmark_input.model_copy(update={"symbol": "SPY_2", "strike": 605, "volume": 500, "gamma": 0.02})
    ]
    inputs_map = {i.symbol: i for i in inps}
    
    d_results = d_engine.compute(inps)
    e_results = e_engine.compute(inps)
    # Simulate G failure
    g_results = [r.model_copy(update={"is_valid": False}) for r in d_results]
    
    composed = composer.compose(d_results, e_results, g_results, inputs_map, gex_regime="NEUTRAL")
    assert len(composed) == 2
    assert composed[0].engine_g_active is False
    logger.info(f"  [PASS] DEG Score for Top Strike: {composed[0].flow_deg:.3f}")
    
    logger.info("=== INSTITUTIONAL AUDIT: COMPLETE & PASSED ===")

if __name__ == "__main__":
    asyncio.run(run_audit())
