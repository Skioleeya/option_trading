"""DepthProfile submodule — UI mappings.

Maps per-strike state flags to CSS color tokens.
All tokens reference the global theme.py.
"""

from app.ui import theme

# Color for put bars (Asian Dragon: green = down)
PUT_BAR_COLOR = f"bg-{theme.MARKET_DOWN}"

# Color for call bars (Asian Dragon: red = up)
CALL_BAR_COLOR = f"bg-{theme.MARKET_UP}"

# Strike labels for special levels
STRIKE_SPOT_COLOR   = f"text-{theme.ACCENT_AMBER} font-bold"
STRIKE_FLIP_COLOR   = f"text-{theme.ACCENT_PURPLE}"
STRIKE_DEFAULT_COLOR = theme.TEXT_SECONDARY
