
import sys
import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, '.')

from app.agents.agent_g import AgentG
from app.agents.base import AgentResult

async def test_micro_flow_integration():
    print("--- Functional Test: Phase 3 Micro Flow Integration ---")
    
    # 1. Setup Mocks
    agent_a_res = AgentResult(
        agent="agent_a",
        signal="BULLISH",
        as_of=datetime.now(),
        data={"spot": 684.0}
    )
    
    # Mock AgentB1 output data
    agent_b_data = {
        "net_gex": 100.0,
        "spy_atm_iv": 15.0,
        "micro_structure": {
            "micro_structure_state": {
                "iv_velocity": {"state": "UNAVAILABLE", "confidence": 0.0},
                "wall_migration": {"call_wall_state": "STABLE", "put_wall_state": "STABLE", "confidence": 0.5},
                "vanna_flow_result": {"state": "UNAVAILABLE", "confidence": 0.0},
                "volume_imbalance": {"consensus": "NEUTRAL", "strength": 0.0},
            }
        },
        "mtf_consensus": {"consensus": "NEUTRAL", "strength": 0.0}
    }

    agent_b_res = AgentResult(
        agent="agent_b1",
        signal="IDLE",
        as_of=datetime.now(),
        data=agent_b_data
    )

    
    # 2. Construct Snapshot with ATM Toxicity/BBO
    snapshot = {
        "per_strike_gex": [
            {"strike": 681.0, "toxicity_score": 0.8, "bbo_imbalance": 0.5}, # ATM-3
            {"strike": 684.0, "toxicity_score": 0.7, "bbo_imbalance": 0.6}, # ATM
            {"strike": 687.0, "toxicity_score": 0.9, "bbo_imbalance": 0.4}, # ATM+3
            {"strike": 700.0, "toxicity_score": 0.1, "bbo_imbalance": 0.1}, # OTM (should be ignored)
        ]
    }
    
    # 3. Initialize AgentG and run decide
    agent_g = AgentG()
    result = await agent_g.decide(agent_a=agent_a_res, agent_b=agent_b_res, snapshot=snapshot)
    
    # 4. Verify results
    fused = result.data.get("fused_signal", {})
    components = fused.get("components", {})
    weights = fused.get("weights", {})
    
    print(f"Fused Direction: {fused.get('direction')}")
    print(f"Components: {list(components.keys())}")
    
    assert "micro_flow" in components, "FAIL: micro_flow missing from components"
    assert "micro_flow" in weights, "FAIL: micro_flow missing from weights"
    
    mf = components["micro_flow"]
    print(f"Micro Flow Detail: dir={mf['direction']}, conf={mf['confidence']:.2f}, weight={mf['weight']:.2%}")
    
    assert mf["direction"] == "BULLISH", f"FAIL: Expected BULLISH micro_flow, got {mf['direction']}"
    assert mf["confidence"] > 0.5, "FAIL: Confidence should be high given testing scores"
    
    print("--- TEST PASSED SUCCESSFULLY ---")

if __name__ == "__main__":
    asyncio.run(test_micro_flow_integration())
