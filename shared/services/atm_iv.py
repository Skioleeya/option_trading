from __future__ import annotations

from typing import Any

import numpy as np


def extract_atm_iv_value(strikes: Any, ivs: Any, spot: float) -> float:
    """Return IV at strike closest to spot."""
    if len(strikes) == 0:
        return 0.0
    idx = int(np.argmin(np.abs(strikes - spot)))
    value = float(ivs[idx])
    return value if value > 0.0 else 0.0
