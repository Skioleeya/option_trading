"""Input diagnostics helpers for ActiveOptions runtime."""

from __future__ import annotations

from typing import Any


def summarize_chain_input(
    *,
    chain: list[dict[str, Any]],
) -> dict[str, int]:
    day_volume_gt_zero = 0
    current_volume_gt_zero = 0
    turnover_gt_zero = 0
    gamma_nonzero = 0
    for row in chain:
        if not isinstance(row, dict):
            continue
        try:
            day_volume = float(row.get("volume", 0.0) or 0.0)
        except (TypeError, ValueError):
            day_volume = 0.0
        try:
            current_volume = float(row.get("current_volume", 0.0) or 0.0)
        except (TypeError, ValueError):
            current_volume = 0.0
        try:
            turnover = float(row.get("turnover", 0.0) or 0.0)
        except (TypeError, ValueError):
            turnover = 0.0
        try:
            gamma = float(row.get("gamma", 0.0) or 0.0)
        except (TypeError, ValueError):
            gamma = 0.0

        if day_volume > 0.0:
            day_volume_gt_zero += 1
        if current_volume > 0.0:
            current_volume_gt_zero += 1
        if turnover > 0.0:
            turnover_gt_zero += 1
        if gamma != 0.0:
            gamma_nonzero += 1
    return {
        "chain_size": len(chain),
        "day_volume_gt_zero": day_volume_gt_zero,
        "current_volume_gt_zero": current_volume_gt_zero,
        "turnover_gt_zero": turnover_gt_zero,
        "gamma_nonzero": gamma_nonzero,
    }
