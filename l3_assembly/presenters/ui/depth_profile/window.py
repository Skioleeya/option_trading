"""Depth-profile strike window selection."""

from __future__ import annotations

def build_contiguous_strikes(
    *,
    center: float,
    spacing: float,
    count: int,
) -> list[float]:
    if count <= 0:
        return []

    # Enforce a fixed odd-window symmetry around center.
    final_count = count if count % 2 == 1 else count + 1
    half = final_count // 2

    start = center - (half * spacing)

    return sorted(
        [round(start + (i * spacing), 2) for i in range(final_count)],
        reverse=True,
    )
