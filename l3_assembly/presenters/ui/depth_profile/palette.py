"""DepthProfile submodule — Palette.

Colors that are ONLY used by the DepthProfile bar chart.
"""

from l3_assembly.presenters.ui import theme

# Horizontal bars
PUT_BAR_COLOR  = f"bg-{theme.MARKET_DOWN}"   # Green bar (put)
CALL_BAR_COLOR = f"bg-{theme.MARKET_UP}"     # Red bar (call)

# Strike center column text
STRIKE_SPOT_COLOR    = "text-accent-amber font-bold"   # Spot price highlight
STRIKE_FLIP_COLOR    = "text-accent-purple"            # Gamma flip highlight
STRIKE_DEFAULT_COLOR = theme.TEXT_SECONDARY            # Normal row

# Bar labels
PUT_LABEL_COLOR  = f"text-{theme.MARKET_DOWN}"
CALL_LABEL_COLOR = f"text-{theme.MARKET_UP}"

# Spot / Flip overlay tags
SPOT_TAG_CLASSES = "text-accent-amber border border-accent-amber/30 bg-accent-amber/10"
FLIP_TAG_CLASSES = "text-accent-purple bg-accent-purple/10 border border-accent-purple/20"
