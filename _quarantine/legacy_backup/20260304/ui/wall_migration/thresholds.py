"""WallMigration submodule — Business thresholds.

Controls data slicing and how Call/Put wall history is passed to frontend.
"""

# Number of historical snapshots to include per row (excluding current)
HISTORY_DEPTH: int = 2
