"""DepthProfile submodule — Business thresholds.

Controls how bar dominance and strike proximity are determined.
"""

# Minimum fraction of max-abs-GEX required for a bar to be "dominant"
# e.g. 0.10 = bar must be at least 10% of the largest bar to earn a P/C label
GEX_DOMINANCE_RATIO: float = 0.10

# Maximum distance from spot/flip to still be highlighted (in strike points)
STRIKE_PROXIMITY_THRESHOLD: float = 0.50
