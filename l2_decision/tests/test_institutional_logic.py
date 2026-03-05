import pytest
from l2_decision.signals.flow.deg_composer import InstitutionalSweepDetector, DEGComposer
from shared.models.flow_engine import FlowEngineInput, FlowEngineOutput, FlowComponentResult
from l2_decision.feature_store.extractors import _MaxImpactExtractor

def test_sweep_detection_positive():
    detector = InstitutionalSweepDetector()
    
    # 1. Prepare inputs with symbols indicating strikes
    symbols = ["SPY260310C00400000", "SPY260310C00401000", "SPY260310C00402000"]
    # 2. Mock high Z-scores (>1.5) to trigger sweep logic
    z_scores = [2.0, 2.0, 2.0]
    
    sweeps = detector.detect(symbols, z_scores)
    
    # All should be True as they are neighbors with high activity
    assert sweeps["SPY260310C00400000"] is True
    assert sweeps["SPY260310C00401000"] is True
    assert sweeps["SPY260310C00402000"] is True

def test_ofii_calculation_logic():
    from shared.models.flow_engine import FlowComponentResult
    composer = DEGComposer()
    
    # Mock inputs with TWO strikes to avoid 0.0 Z-score (std dev > 0)
    s1, s2 = "SYM1", "SYM2"
    inputs = {
        s1: FlowEngineInput(
            symbol=s1, option_type="CALL", strike=100.0, spot=100.0,
            volume=1000, turnover=500000.0, implied_volatility=0.2, historical_volatility=0.2,
            open_interest=5000, last_price=5.0,
            contract_multiplier=100.0, delta=0.5, gamma=0.05, vanna=0.01
        ),
        s2: FlowEngineInput(
            symbol=s2, option_type="PUT", strike=90.0, spot=100.0,
            volume=500, turnover=200000.0, implied_volatility=0.2, historical_volatility=0.2,
            open_interest=2000, last_price=2.0,
            contract_multiplier=100.0, delta=-0.3, gamma=0.02, vanna=0.01
        )
    }
    
    # Mock engine results: S1 is high, S2 is low
    # For S1: Z will be positive. For S2: Z will be negative.
    res_d = [
        FlowComponentResult(symbol=s1, strike=100.0, option_type="CALL", flow_value=10.0),
        FlowComponentResult(symbol=s2, strike=90.0, option_type="PUT", flow_value=2.0)
    ]
    res_e = [
        FlowComponentResult(symbol=s1, strike=100.0, option_type="CALL", flow_value=8.0),
        FlowComponentResult(symbol=s2, strike=90.0, option_type="PUT", flow_value=4.0)
    ]
    res_g = [
        FlowComponentResult(symbol=s1, strike=100.0, option_type="CALL", flow_value=5.0),
        FlowComponentResult(symbol=s2, strike=90.0, option_type="PUT", flow_value=1.0)
    ]
    
    # OFII calculation in compose()
    outputs = composer.compose(res_d, res_e, res_g, inputs, ttm_seconds=0)
    
    assert len(outputs) == 2
    out = [o for o in outputs if o.symbol == s1][0]
    assert out.impact_index > 0
    # S1 has higher values, so its Z-scores should be ~1.0
    # weighted sum should be ~1.0
    assert out.flow_deg > 0.5 
    assert out.flow_intensity in ("HIGH", "EXTREME", "MODERATE")

def test_max_impact_extractor():
    extractor = _MaxImpactExtractor()
    
    class MockSnapshot:
        def __init__(self, chain):
            self.chain = chain
    
    # Impact = turnover/volume * gamma
    chain = [
        {"symbol": "S1", "turnover": 1000.0, "gamma": 0.01}, # Impact 10.0
        {"symbol": "S2", "turnover": 2000.0, "gamma": 0.02}, # Impact 40.0 -> Peak
        {"symbol": "S3", "volume": 500, "gamma": 0.05},     # Impact 25.0
    ]
    
    snapshot = MockSnapshot(chain)
    max_imp = extractor(snapshot)
    assert max_imp == 40.0
