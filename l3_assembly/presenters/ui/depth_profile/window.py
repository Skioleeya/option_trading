"""Depth-profile strike window selection."""

from __future__ import annotations

import math


def build_contiguous_strikes(
    *,
    center: float,
    spacing: float,
    count: int,
    flip_level: float | None,
) -> list[float]:
    if count <= 0:
        return []

    half = count // 2
    start = center - (half * spacing)
    end = start + ((count - 1) * spacing)

    if flip_level is not None and math.isfinite(flip_level):
        if flip_level > end:
            shift = math.ceil((flip_level - end) / spacing)
            start += shift * spacing
        elif flip_level < start:
            shift = math.ceil((start - flip_level) / spacing)
            start -= shift * spacing

    return sorted(
        [round(start + (i * spacing), 2) for i in range(count)],
        reverse=True,
    )
