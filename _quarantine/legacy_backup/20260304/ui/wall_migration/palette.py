"""WallMigration submodule — Palette.

Colors that are ONLY used by the WallMigration row table.
"""

# Call (C) row
CALL_TYPE_LABEL = "C"
CALL_TYPE_BG    = "wall-call"          # CSS variable bg-wall-call
CALL_TYPE_TEXT  = "text-market-up"     # Red text (Asian Dragon: up = red)
CALL_DOT_COLOR  = "bg-accent-red"

# Put (P) row
PUT_TYPE_LABEL = "P"
PUT_TYPE_BG    = "wall-put"            # CSS variable bg-wall-put
PUT_TYPE_TEXT  = "text-market-down"    # Green text (Asian Dragon: down = green)
PUT_DOT_COLOR  = "bg-accent-green"

# Highlighted current-value box (shared amber glow — defined once here)
CURRENT_BOX_BORDER = "rgba(245, 158, 11, 0.7)"
CURRENT_BOX_BG     = "rgba(245, 158, 11, 0.08)"
CURRENT_BOX_SHADOW = "rgba(245, 158, 11, 0.25)"
CURRENT_TEXT_CLASS = "text-accent-amber font-bold"
