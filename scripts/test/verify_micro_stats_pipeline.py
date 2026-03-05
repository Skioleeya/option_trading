import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
from dataclasses import dataclass, field

# Setup python path to include project root
root = Path(__file__).parent.parent.parent
sys.path.append(str(root))

from l3_assembly.assembly.ui_state_tracker import UIStateTracker

@dataclass
class MockAggregates:
    atm_iv: float = 0.20
    net_gex: float = 500.0
    call_wall: float = 500.0
    put_wall: float = 480.0
    net_charm: float = 0.01

@dataclass
class MockSnapshot:
    spot: float = 490.0
    aggregates: MockAggregates = field(default_factory=MockAggregates)
    microstructure: Any = None

@dataclass
class MockDecision:
    signal_summary: dict[str, Any] = None
    feature_vector: dict[str, Any] = None

def test_micro_stats_momentum_fix():
    print("Testing MicroStats Momentum Fix...")
    
    tracker = UIStateTracker()
    
    # Mock snapshot
    snapshot = MockSnapshot()
    
    # Mock decision with dictionary momentum signal (New L2 Architecture)
    decision = MockDecision(
        signal_summary={
            "momentum_signal": {"direction": "BULLISH", "confidence": 0.85},
            "flow_analyzer": {"direction": "NEUTRAL", "confidence": 0.0}
        },
        feature_vector={"skew_25d_normalized": 0.0}
    )
    
    # Tick the tracker
    metrics = tracker.tick(snapshot, decision)
    
    # Verify momentum is a string, not a dict
    momentum = metrics.get("momentum")
    print(f"Extracted momentum: {momentum} (Type: {type(momentum)})")
    
    assert isinstance(momentum, str), f"Expected string momentum, got {type(momentum)}"
    assert momentum == "BULLISH", f"Expected BULLISH, got {momentum}"
    
    # Also verify GEX regime and Vanna state (defaults)
    print(f"GEX Regime: {metrics.get('gex_regime')}")
    print(f"Vanna State: {metrics.get('vanna_state')}")
    
    print("SUCCESS: MicroStats Momentum Type Mismatch Resolved.")

def test_wall_migration_mapping():
    print("\nTesting Wall Migration Mapping...")
    # This is more of a logic check for AgentG's internal mapping
    from l2_decision.agents.agent_g import AgentG
    agent = AgentG()
    
    # Test BREACHED mapping
    dir_call = agent._map_wall_to_direction("BREACHED", "STABLE")
    dir_put = agent._map_wall_to_direction("STABLE", "BREACHED")
    
    print(f"Call BREACHED -> {dir_call}")
    print(f"Put BREACHED -> {dir_put}")
    
    assert dir_call == "BULLISH"
    assert dir_put == "BEARISH"
    
    print("SUCCESS: Wall Migration BREACHED Mapping Verified.")

if __name__ == "__main__":
    try:
        test_micro_stats_momentum_fix()
        test_wall_migration_mapping()
        print("\nAll MicroStats and Wall Migration verification tests PASSED.")
    except Exception as e:
        print(f"\nFAILURE: {e}")
        sys.exit(1)
