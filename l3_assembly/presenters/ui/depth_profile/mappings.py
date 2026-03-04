"""DepthProfile submodule — UI mappings.

Maps per-strike state flags to CSS color tokens.
Imports from this submodule's own palette — not from global theme.
"""

from l3_assembly.presenters.ui.depth_profile import palette

# Bar colors
PUT_BAR_COLOR  = palette.PUT_BAR_COLOR
CALL_BAR_COLOR = palette.CALL_BAR_COLOR

# Strike center text colors
STRIKE_SPOT_COLOR    = palette.STRIKE_SPOT_COLOR
STRIKE_FLIP_COLOR    = palette.STRIKE_FLIP_COLOR
STRIKE_DEFAULT_COLOR = palette.STRIKE_DEFAULT_COLOR

# Labels on dominant bars
PUT_LABEL_COLOR  = palette.PUT_LABEL_COLOR
CALL_LABEL_COLOR = palette.CALL_LABEL_COLOR

# Overlay annotation tags
SPOT_TAG_CLASSES = palette.SPOT_TAG_CLASSES
FLIP_TAG_CLASSES = palette.FLIP_TAG_CLASSES
