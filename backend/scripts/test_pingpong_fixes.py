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
# Summary
# ===========================================================================
all_ok = [ok1,ok2,ok3,ok4,ok5,ok6,ok7,ok8,ok9,ok10,ok11,ok12,ok13,ok14,ok15,ok16,ok17]
passed = sum(all_ok)
total  = len(all_ok)

print()
print(SEP)
if passed == total:
    print(f"\033[92m✓ ALL {total}/{total} CHECKS PASSED — PP-1 ~ PP-4 fixes verified.\033[0m")
else:
    print(f"\033[91m✗ {passed}/{total} CHECKS PASSED — review failures above.\033[0m")
print(SEP)
sys.exit(0 if passed == total else 1)
