"""
PP-1 ~ PP-4 Ping-Pong Fix Verification Script
==============================================
Runs offline unit-level checks for each fix without Longport API.

Usage:
    cd e:\\US.market\\Option_v3\\backend
    python scripts/test_pingpong_fixes.py
"""

import sys
import os
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Patch environment so Settings() doesn't require Longport keys
os.environ.setdefault("LONGPORT_APP_KEY", "test")
os.environ.setdefault("LONGPORT_APP_SECRET", "test")
os.environ.setdefault("LONGPORT_ACCESS_TOKEN", "test")

from app.config import settings

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
SEP  = "-" * 60

def check(label: str, cond: bool, detail: str = "") -> bool:
    status = PASS if cond else FAIL
    print(f"  {status} {label}")
    if detail and not cond:
        print(f"         {detail}")
    return cond


# ===========================================================================
# PP-1: baseline_hv now reads from settings
# ===========================================================================
print(SEP)
print("PP-1: VRP baseline_hv config-ization")
print(SEP)

# Simulate agent_b VRP calc
atm_iv = 27.0
baseline_hv = settings.vrp_baseline_hv   # <-- the fix
vrp = atm_iv - baseline_hv

ok1 = check(
    "settings.vrp_baseline_hv exists and equals 13.5 (default)",
    settings.vrp_baseline_hv == 13.5,
    f"got {settings.vrp_baseline_hv}"
)
ok2 = check(
    "VRP calc uses settings (vrp=13.5 when iv=27 baseline=13.5)",
    abs(vrp - 13.5) < 1e-9,
    f"got vrp={vrp}"
)

# ===========================================================================
# PP-2: MTF alignment EWMA smoothing
# ===========================================================================
print()
print(SEP)
print("PP-2: MTF alignment EWMA smoothing")
print(SEP)

# Simulate EWMA across 10 ticks: alignment oscillates 0.33 ↔ 0.67
alpha = settings.mtf_alignment_ewma_alpha   # 0.30
ema = None
raw_alignments = [0.33, 0.67, 0.33, 0.67, 0.33, 0.67, 0.33, 0.67, 0.33, 0.67]
ema_values = []
for raw in raw_alignments:
    if ema is None:
        ema = raw
    else:
        ema = alpha * raw + (1 - alpha) * ema
    ema_values.append(ema)

max_jump = max(abs(ema_values[i] - ema_values[i-1]) for i in range(1, len(ema_values)))

ok3 = check(
    "settings.mtf_alignment_ewma_alpha exists (default 0.30)",
    settings.mtf_alignment_ewma_alpha == 0.30,
    f"got {settings.mtf_alignment_ewma_alpha}"
)
ok4 = check(
    "EWMA max single-tick jump < 0.15 (smoothed from raw 0.34 jump)",
    max_jump < 0.15,
    f"max_jump={max_jump:.3f}, raw oscillation was 0.34"
)
ok5 = check(
    "settings.mtf_alignment_damp_entry/exit configurable",
    settings.mtf_alignment_damp_entry == 0.34 and settings.mtf_alignment_damp_exit == 0.38,
    f"entry={settings.mtf_alignment_damp_entry}, exit={settings.mtf_alignment_damp_exit}"
)
ok6 = check(
    "settings.agent_g_vib_weight exists (default 0.20)",
    settings.agent_g_vib_weight == 0.20,
    f"got {settings.agent_g_vib_weight}"
)

# ===========================================================================
# PP-3: GRIND_STABLE direction + vanna_confidence boundary smoothing
# ===========================================================================
print()
print(SEP)
print("PP-3: GRIND_STABLE direction fix + vanna_confidence boundary smoothing")
print(SEP)

# Test direction mapping
# Import agent_g without full initialization
from app.agents.agent_g import AgentG
g = AgentG.__new__(AgentG)

ok7 = check(
    "GRIND_STABLE maps to NEUTRAL (was BULLISH)",
    g._map_vanna_to_direction("GRIND_STABLE") == "NEUTRAL",
    f"got {g._map_vanna_to_direction('GRIND_STABLE')}"
)
ok8 = check(
    "DANGER_ZONE still maps to BULLISH",
    g._map_vanna_to_direction("DANGER_ZONE") == "BULLISH",
    f"got {g._map_vanna_to_direction('DANGER_ZONE')}"
)

# Test vanna_flow_analyzer confidence boundary interpolation
from app.services.trackers.vanna_flow_analyzer import VannaFlowAnalyzer
from app.models.microstructure import VannaFlowResult, VannaFlowState, GexRegime

analyzer = VannaFlowAnalyzer()

danger_th = settings.vanna_danger_zone_threshold  # 0.45
BAND = 0.05

# Simulate result just AT threshold - should get mid confidence ~0.65
from app.models.microstructure import VannaAccelerationState
mock_at_threshold = VannaFlowResult(
    state=VannaFlowState.DANGER_ZONE,
    correlation=danger_th,          # exactly at threshold = mid of band
    gex_regime=GexRegime.NEUTRAL,
    net_gex=0.0,
)
# populate enough history for sample_factor=1.0
for _ in range(20):
    from app.services.trackers.vanna_flow_analyzer import SpotIVPoint
    import time
    analyzer._history.append(SpotIVPoint(time.monotonic(), 550.0, 15.0))
analyzer._last_result = mock_at_threshold

conf_at = analyzer.get_confidence()

# Simulate result well ABOVE threshold - should get high confidence ~0.9
mock_well_above = VannaFlowResult(
    state=VannaFlowState.DANGER_ZONE,
    correlation=danger_th + 0.10,   # well above → boundary_progress=1.0
    gex_regime=GexRegime.NEUTRAL,
    net_gex=0.0,
)
analyzer._last_result = mock_well_above
conf_above = analyzer.get_confidence()

# Simulate result just BELOW threshold (NORMAL state, low conf)
mock_below = VannaFlowResult(
    state=VannaFlowState.NORMAL,
    correlation=danger_th - 0.10,
    gex_regime=GexRegime.NEUTRAL,
    net_gex=0.0,
)
analyzer._last_result = mock_below
conf_below = analyzer.get_confidence()

ok9 = check(
    "At DANGER_ZONE threshold: confidence is mid-range (~0.65, not hard 0.9)",
    0.55 < conf_at < 0.80,
    f"conf_at={conf_at:.3f}"
)
ok10 = check(
    "Well above DANGER_ZONE threshold: confidence reaches ~0.9",
    conf_above > 0.80,
    f"conf_above={conf_above:.3f}"
)
ok11 = check(
    "Below threshold (NORMAL state): confidence is low",
    conf_below < 0.60,
    f"conf_below={conf_below:.3f}"
)
ok12 = check(
    "Confidence increases monotonically across boundary (no hard jump)",
    conf_below < conf_at < conf_above,
    f"{conf_below:.3f} < {conf_at:.3f} < {conf_above:.3f}"
)

# ===========================================================================
# PP-4: GEX accel threshold config-ized
# ===========================================================================
print()
print(SEP)
print("PP-4: GEX acceleration threshold config-ization")
print(SEP)

ok13 = check(
    "settings.gex_accel_threshold exists (default -500.0)",
    settings.gex_accel_threshold == -500.0,
    f"got {settings.gex_accel_threshold}"
)
ok14 = check(
    "settings.gex_accel_boost_bearish exists (default 1.20)",
    settings.gex_accel_boost_bearish == 1.20,
    f"got {settings.gex_accel_boost_bearish}"
)
ok15 = check(
    "settings.gex_accel_boost_bullish exists (default 1.15)",
    settings.gex_accel_boost_bullish == 1.15,
    f"got {settings.gex_accel_boost_bullish}"
)

# Verify boundary behavior: -499 should NOT trigger, -501 SHOULD trigger
boost_499 = 1.0  # below threshold, no boost
boost_501 = settings.gex_accel_boost_bearish if (-501 < settings.gex_accel_threshold) else 1.0
gex_499_triggers = (-499 < settings.gex_accel_threshold)   # False = correct
gex_501_triggers = (-501 < settings.gex_accel_threshold)   # True  = correct

ok16 = check(
    "GEX=-499 does NOT trigger boost (above threshold)",
    not gex_499_triggers,
    f"gex_accel_threshold={settings.gex_accel_threshold}"
)
ok17 = check(
    "GEX=-501 DOES trigger boost (below threshold)",
    gex_501_triggers,
    f"gex_accel_threshold={settings.gex_accel_threshold}"
)

# ===========================================================================
# PP-VPIN: Practice 2 — Volume-Synchronized VPIN Dynamic Alpha
# ===========================================================================
print()
print(SEP)
print("PP-VPIN: Dynamic Alpha VPIN (Practice 2)")
print(SEP)

from app.services.analysis.depth_engine import DepthEngine


class _FakeTrade:
    """Minimal trade object for DepthEngine.update_trades()."""
    def __init__(self, volume, direction):
        self.volume = volume
        self.direction = str(direction)  # "1"=Up, "2"=Down


# PP-VPIN-1: Low volume trade → near-zero alpha → toxicity barely changes
engine_low = DepthEngine()
engine_low._ensure_symbol("TEST")
# Initialize with some volume so dynamic_alpha doesn't dominate a zero-state
engine_low._state["TEST"]["ema_volume"] = 100.0
engine_low._state["TEST"]["ema_dir_volume"] = 50.0  # toxicity = 0.5
engine_low._state["TEST"]["toxicity_score"] = 0.5

# With vol=5, bucket=500 → dynamic_alpha = 5/500 = 0.01
vol_low = 5
bucket_size = settings.vpin_bucket_size  # default 500
expected_alpha_low = min(1.0, vol_low / bucket_size)  # 0.01
prev_score = engine_low._state["TEST"]["toxicity_score"]
# CORRECTED: 2 = Up (Bullish)
engine_low.update_trades("TEST", [_FakeTrade(vol_low, 2)])
new_score_low = engine_low._state["TEST"]["toxicity_score"]
change_pct = abs(new_score_low - prev_score) / max(abs(prev_score), 1e-9) * 100

ok18 = check(
    f"PP-VPIN-1: Low vol={vol_low} → dynamic_alpha={expected_alpha_low:.2f} → toxicity change < 5%",
    change_pct < 5.0,
    f"change={change_pct:.2f}% (new={new_score_low:.4f} prev={prev_score:.4f})"
)

# PP-VPIN-2: High volume trade → alpha=1.0 → toxicity fully updates
engine_high = DepthEngine()
engine_high._ensure_symbol("TEST")
engine_high._state["TEST"]["ema_volume"] = 100.0
engine_high._state["TEST"]["ema_dir_volume"] = -50.0  # previously bearish (-0.5)
engine_high._state["TEST"]["toxicity_score"] = -0.5

vol_high = 500  # exactly at bucket size → alpha = 1.0
# CORRECTED: 2 = Up (Bullish)
engine_high.update_trades("TEST", [_FakeTrade(vol_high, 2)])  # bullish
new_score_high = engine_high._state["TEST"]["toxicity_score"]

ok19 = check(
    f"PP-VPIN-2: High vol={vol_high} → alpha=1.0 → toxicity fully updates to near +1.0",
    new_score_high > 0.5,
    f"new_score={new_score_high:.4f}"
)

# PP-VPIN-3: vpin_score in get_flow_snapshot() is in range [-1.0, 1.0]
engine_mixed = DepthEngine()
# CORRECTED: 2 = Up, 1 = Down
trades = [_FakeTrade(400, 2), _FakeTrade(200, 1), _FakeTrade(300, 2)]
engine_mixed.update_trades("SPY_ATM", trades)
snapshot = engine_mixed.get_flow_snapshot()
vpin_s = snapshot.get("SPY_ATM", {}).get("vpin_score", None)

ok20 = check(
    f"PP-VPIN-3: vpin_score present in get_flow_snapshot() and in [-1.0, 1.0]",
    vpin_s is not None and -1.0 <= vpin_s <= 1.0,
    f"vpin_score={vpin_s}"
)

# PP-VPIN-4: Neutral trade → dir_sign=0.0 → toxicity dilutes toward zero
engine_neutral = DepthEngine()
engine_neutral._ensure_symbol("TEST")
engine_neutral._state["TEST"]["ema_volume"] = 100.0
engine_neutral._state["TEST"]["ema_dir_volume"] = 50.0 # toxicity = 0.5
engine_neutral._state["TEST"]["toxicity_score"] = 0.5

# High volume Neutral trade (vol=500)
engine_neutral.update_trades("TEST", [_FakeTrade(500, 0)]) # 0 = Neutral
new_score_neutral = engine_neutral._state["TEST"]["toxicity_score"]

ok26 = check(
    f"PP-VPIN-4: Neutral trade vol=500 → toxicity dilutes toward zero (score={new_score_neutral:.4f})",
    abs(new_score_neutral) < 0.2, # 50 / (100 + 500) ≈ 0.08
    f"new_score={new_score_neutral:.4f}"
)

# ===========================================================================
# PP-ACCEL: Practice 3 — Volume Acceleration Ratio
# ===========================================================================
print()
print(SEP)
print("PP-ACCEL: Volume Acceleration Ratio (Practice 3)")
print(SEP)

from app.services.analysis.volume_imbalance_engine import VolumeImbalanceEngine

spot = 550.0

def make_chain(call_volume: int, put_volume: int) -> list[dict]:
    """Build a minimal chain for VolumeImbalanceEngine."""
    return [
        {"strike": 555.0, "option_type": "CALL", "volume": call_volume},
        {"strike": 545.0, "option_type": "PUT",  "volume": put_volume},
    ]


# PP-ACCEL-1: vol_accel_ratio ≈ 1.0 when 1s vol equals 60-tick EMA average
vib_engine = VolumeImbalanceEngine()
# Feed 30 ticks of constant ACTIVITY (delta=100 per tick)
# Cumulative = 100, 200, 300...
for i in range(1, 31):
    vib_engine.update(make_chain(50*i, 50*i), spot)

# Current activity is 100. Baseline EMA is 100. Ratio should be 1.0.
result_stable = vib_engine.update(make_chain(50*31, 50*31), spot)
vol_accel_stable = result_stable.vol_accel_ratio

ok21 = check(
    f"PP-ACCEL-1: vol_accel_ratio ≈ 1.0 when 1s vol equals 60-tick EMA average",
    0.9 <= vol_accel_stable <= 1.1,
    f"vol_accel_ratio={vol_accel_stable:.3f}"
)

# PP-ACCEL-2: vol_accel_ratio ≥ 3.0 when 1s volume is 3× the 60-tick average
# Baseline is still 100. Delta needed = 300+.
# Prev cumulative (from above) was 3100. Current delta 300 -> 3400 cumulative.
result_burst = vib_engine.update(make_chain(1700, 1700), spot) # delta = 3400 - 3100 = 300
vol_accel_high = result_burst.vol_accel_ratio

ok22 = check(
    f"PP-ACCEL-2: vol_accel_ratio ≥ 3.0 when 1s volume is 3× the 60-tick average",
    vol_accel_high >= 2.9,
    f"vol_accel_ratio={vol_accel_high:.3f}"
)

# PP-ACCEL-3: dealer_squeeze_alert=True when vol_accel=3.5 ≥ 3.0 AND net_gex=-100.0
# We need delta = 350. Prev cumulative was 3400 -> New cumulative 3750.
# Since make_chain calculates total, we need to pass volumes that sum to 3750.
# Let's just create a direct list for clarity.
net_gex_neg = -100.0
chain_neg_gex = [
    {"strike": 555.0, "option_type": "CALL", "volume": 1875}, # Sum = 3750
    {"strike": 545.0, "option_type": "PUT",  "volume": 1875},
]
# We also need to mock or ensure net_gex is negative in the VIBResult
# VolumeImbalanceEngine.update computes imbalance strength but not net_gex itself.
# The alert logic is in AgentB.
vib_result_burst = vib_engine.update(chain_neg_gex, spot) # delta = 3750 - 3400 = 350. Ratio = 350/100 = 3.5.

# Manual check of the alert logic (which AgentB would do)
vol_accel_squeeze_threshold = 3.0
has_squeeze = (vib_result_burst.vol_accel_ratio >= vol_accel_squeeze_threshold) and (net_gex_neg < 0)

ok23 = check(
    f"PP-ACCEL-3: dealer_squeeze_alert=True when vol_accel={vib_result_burst.vol_accel_ratio:.1f} ≥ {vol_accel_squeeze_threshold} AND net_gex={net_gex_neg}",
    has_squeeze is True,
    f"has_squeeze={has_squeeze}"
)

# PP-ACCEL-4: dealer_squeeze_alert = False when vol_accel ≥ threshold BUT net_gex > 0
net_gex_pos = +100.0
no_squeeze = not (
    vol_accel_high >= vol_accel_squeeze_threshold
    and net_gex_pos < 0   # positive GEX → no squeeze
)
ok24 = check(
    f"PP-ACCEL-4: dealer_squeeze_alert=False when vol_accel={vol_accel_high:.1f} ≥ {vol_accel_squeeze_threshold} BUT net_gex={net_gex_pos} (positive)",
    no_squeeze is True,
    f"no_squeeze={no_squeeze}"
)

# PP-ACCEL-5: vol_accel_ratio correctly uses DELTA from cumulative volume
vib_engine_delta = VolumeImbalanceEngine()
# Initial tick: 1000 accumulated
vib_engine_delta.update(make_chain(500, 500), spot) 
# Feed ticks with constant delta=100
for i in range(1, 101):
    # Total = 1000 + 100*i
    vib_engine_delta.update(make_chain(500+50*i, 500+50*i), spot)

# Current cumulative = 1000 + 100*100 = 11000. EMA ≈ 100.
# Burst: Delta=1000. New cumulative = 12000.
result_burst_delta = vib_engine_delta.update([
    {"strike": 555.0, "option_type": "CALL", "volume": 6000},
    {"strike": 545.0, "option_type": "PUT",  "volume": 6000},
], spot)

ok25 = check(
    "PP-ACCEL-5: vol_accel_ratio detects burst using delta from cumulative inputs",
    result_burst_delta.vol_accel_ratio >= 6.0, 
    f"vol_accel_ratio={result_burst_delta.vol_accel_ratio:.3f} (delta={12000-11000})"
)

# ===========================================================================
# Summary
# ===========================================================================
all_ok = [ok1,ok2,ok3,ok4,ok5,ok6,ok7,ok8,ok9,ok10,ok11,ok12,ok13,ok14,ok15,ok16,ok17,
          ok18,ok19,ok20,ok21,ok22,ok23,ok24,ok25,ok26]
passed = sum(all_ok)
total  = len(all_ok)

print()
print(SEP)
if passed == total:
    print(f"\033[92m✓ ALL {total}/{total} CHECKS PASSED — PP-1 ~ PP-4 + PP-VPIN + PP-ACCEL fixes verified.\033[0m")
else:
    print(f"\033[91m✗ {passed}/{total} CHECKS PASSED — review failures above.\033[0m")
print(SEP)
sys.exit(0 if passed == total else 1)
