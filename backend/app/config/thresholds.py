"""Business Logic Thresholds & Configuration.

Contains centralized thresholds, ratios, and constants used by Agents and Presenters 
to determine state without hardcoding numeric values into business logic.
"""

# ---------------------------------------------------------------------------
# Depth Profile / GEX Thresholds
# ---------------------------------------------------------------------------
# Minimum absolute GEX required for a put or call bar to be considered "dominant"
# relative to the maximum GEX across all strikes.
GEX_DOMINANCE_RATIO = 0.10

# Proximity threshold for identifying SPOT or FLIP levels (distance to strike)
STRIKE_PROXIMITY_THRESHOLD = 0.50

# ---------------------------------------------------------------------------
# Interactive Hover & Magnet Settings
# ---------------------------------------------------------------------------
# Minimum width in % (or px) for an option bar to be visible in DepthProfile
MIN_VISIBLE_BAR_PCT = 1.0
