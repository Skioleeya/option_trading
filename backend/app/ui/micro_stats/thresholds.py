"""MicroStats submodule — Business thresholds.

Controls when Agent states trigger UI transitions.
Modify here to change sensitivity without touching presenter logic.
"""

# --- NET GEX Regime ---
# These strings must match what AgentB/Vanna returns as gex_regime
GEX_REGIME_SUPER_PIN = "SUPER_PIN"
GEX_REGIME_DAMPING = "DAMPING"
GEX_REGIME_ACCELERATION = "ACCELERATION"
GEX_REGIME_NEUTRAL = "NEUTRAL"

# --- WALL DYN thresholds ---
# Call / Put wall states that trigger a SIEGE badge
WALL_SIEGE_STATES = {"REINFORCED_WALL", "REINFORCED_SUPPORT"}

# Call wall states that trigger RETREAT badge
WALL_RETREAT_STATES = {"RETREATING_RESISTANCE"}
