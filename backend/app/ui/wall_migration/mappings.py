"""WallMigration submodule — UI mappings.

Maps Call/Put type to CSS color tokens for the bidirectional row view.
All tokens reference the global theme.py.
"""

from app.ui import theme

# Call Wall row
CALL_TYPE_LABEL = "C"
CALL_TYPE_BG    = theme.BG_WALL_CALL     # bg-wall-call (Tailwind)
CALL_TYPE_TEXT  = f"text-{theme.MARKET_UP}"
CALL_DOT_COLOR  = f"bg-{theme.ACCENT_RED}"

# Put Wall row
PUT_TYPE_LABEL = "P"
PUT_TYPE_BG    = theme.BG_WALL_PUT       # bg-wall-put (Tailwind)
PUT_TYPE_TEXT  = f"text-{theme.MARKET_DOWN}"
PUT_DOT_COLOR  = f"bg-{theme.ACCENT_GREEN}"
