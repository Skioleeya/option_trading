from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tools.momentum_calibration.sources.research_adapter import ResearchFeatureProvider

ET = ZoneInfo("America/New_York")


def test_research_provider_returns_none_for_now() -> None:
    p = ResearchFeatureProvider()
    out = p.load(
        datetime(2026, 3, 10, 9, 30, tzinfo=ET),
        datetime(2026, 3, 10, 16, 0, tzinfo=ET),
        "SPY.US",
    )
    assert out is None

