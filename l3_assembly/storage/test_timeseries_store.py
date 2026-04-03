from __future__ import annotations

import pytest

from l3_assembly.storage.timeseries_store import TimeSeriesStoreV2


class _DummyPayload:
    def __init__(self, value: int) -> None:
        self._value = value

    def to_dict(self) -> dict[str, int]:
        return {"value": self._value}


@pytest.mark.asyncio
async def test_get_warm_latest_without_redis_does_not_fallback_to_hot() -> None:
    store = TimeSeriesStoreV2(redis=None)
    await store.write(_DummyPayload(1))

    rows = await store.get_warm_latest(10)

    assert rows == []
