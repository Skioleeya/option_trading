"""Global Shared Theme Tokens.

Only colors that are used across MULTIPLE submodules live here.
Module-specific colors belong in each submodule's palette.py.

Rule: if only one submodule references a color, it does NOT belong here.
"""

# ── Market Direction Colors (used everywhere) ──────────────────────────────
MARKET_UP      = "market-up"      # Red in Asian Dragon (price up)
MARKET_DOWN    = "market-down"    # Green in Asian Dragon (price down)
MARKET_NEUTRAL = "market-neutral"

# ── Badge System (used by all MicroStats + GexStatusBar) ───────────────────
BADGE_NEUTRAL      = "badge-neutral"
BADGE_AMBER        = "badge-amber"
BADGE_GREEN        = "badge-green"
BADGE_RED          = "badge-red"
BADGE_PURPLE       = "badge-purple"
BADGE_CYAN         = "badge-cyan"
BADGE_HOLLOW_PURPLE = "badge-hollow-purple"
BADGE_HOLLOW_AMBER  = "badge-hollow-amber"
BADGE_HOLLOW_CYAN   = "badge-hollow-cyan"

# ── Universal Text Helpers ─────────────────────────────────────────────────
TEXT_SECONDARY = "text-text-secondary"
