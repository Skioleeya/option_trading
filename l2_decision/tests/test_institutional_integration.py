import pytest
import asyncio
from datetime import datetime
from l2_decision.reactor import L2DecisionReactor
from l2_decision.events.decision_events import DecisionOutput

@pytest.mark.asyncio
async def test_reactor_integration_impact_telemetry():
    reactor = L2DecisionReactor(enable_audit_disk=False)
    
    # Mock EnrichedSnapshot
    class MockEnrichedSnapshot:
        def __init__(self):
            self.version = 123
            self.spot = 400.0
            self.chain = [
                {"symbol": "S1", "turnover": 1000000.0, "gamma": 0.01, "strike": 400.0, "type": "CALL"},
                {"symbol": "S2", "turnover": 5000000.0, "gamma": 0.02, "strike": 401.0, "type": "CALL"},
            ]
            self.aggregate_greeks = {"atm_iv": 0.2, "net_gex": 1000.0}
            self.microstructure = None
            self.as_of = datetime.now()

    snapshot = MockEnrichedSnapshot()
    
    # Process through reactor
    output = await reactor.decide(snapshot)
    
    assert isinstance(output, DecisionOutput)
    # Peak Impact logic in _MaxImpactExtractor: max(|Turnover| * |Gamma|)
    # S2: 5M * 0.02 = 100,000
    assert output.max_impact == 100000.0
    
    # Verify Audit Trail
    audit_entries = reactor.audit.recent(1)
    assert len(audit_entries) == 1
    assert audit_entries[0].max_impact == 100000.0
    print(f"Integration Success: Peak Impact {output.max_impact} captured in Audit.")

if __name__ == "__main__":
    asyncio.run(test_reactor_integration_impact_telemetry())
