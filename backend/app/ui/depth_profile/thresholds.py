"""DepthProfile submodule — Business thresholds.

Controls how bar dominance and strike proximity are determined.
"""

# Minimum fraction of max-abs-GEX required for a bar to be "dominant"
# e.g. 0.222 = bar must be at least 22.2% of the largest bar to earn a P/C label (was 20px / 90px)
GEX_DOMINANCE_RATIO: float = 0.222

# Number of strikes to show above and below the spot price
STRIKE_RADIUS: int = 8

# Maximum distance from spot/flip to still be highlighted (in strike points)
STRIKE_PROXIMITY_THRESHOLD: float = 0.50
