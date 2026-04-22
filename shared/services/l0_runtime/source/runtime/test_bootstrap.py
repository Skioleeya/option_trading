from __future__ import annotations

from types import SimpleNamespace

import pytest

from shared.services.l0_runtime.source.runtime.bootstrap import _startup_connectivity_probe


class _FakeRuntime:
    def __init__(self, rows):
        self._rows = rows

    async def quote(self, symbols):
        assert symbols == ["SPY.US"]
        return self._rows

    def diagnostics(self):
        return {
            "endpoint_profile": "primary",
            "endpoint_http_url": "https://openapi.longportapp.com",
        }


@pytest.mark.asyncio
async def test_startup_connectivity_probe_returns_initial_spot() -> None:
    runtime = _FakeRuntime([SimpleNamespace(last_done="706.74")])

    spot = await _startup_connectivity_probe(runtime, strict_connectivity=True)

    assert spot == 706.74


@pytest.mark.asyncio
async def test_startup_connectivity_probe_rejects_non_positive_quote() -> None:
    runtime = _FakeRuntime([SimpleNamespace(last_done="0")])

    with pytest.raises(RuntimeError, match="non-positive"):
        await _startup_connectivity_probe(runtime, strict_connectivity=True)
