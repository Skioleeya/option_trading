from __future__ import annotations

import pytest

from shared.services.active_options_runtime import (
    ActiveOptionsHardFailure,
    ActiveOptionsRuntimeService,
)


def _build_service_stub() -> ActiveOptionsRuntimeService:
    svc = ActiveOptionsRuntimeService.__new__(ActiveOptionsRuntimeService)
    svc._latest_payload = []
    svc._latest_signature = None
    svc._pending_signature = None
    svc._pending_rows = []
    svc._pending_hits = 0
    svc._switch_confirm_ticks = 1
    svc._empty_filter_count = 0
    svc._last_empty_filter_at_utc = None
    svc._last_filtered_candidates_count = 0
    svc._last_update_at_utc = None
    svc._halted = False
    svc._halt_reason = None
    svc._halted_at_utc = None
    return svc


@pytest.mark.asyncio
async def test_update_background_hard_fails_when_filtered_candidates_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    svc = _build_service_stub()
    monkeypatch.setattr(
        ActiveOptionsRuntimeService,
        "_normalize_and_filter_chain",
        staticmethod(lambda *, chain, min_volume: []),
    )

    with pytest.raises(ActiveOptionsHardFailure, match="subthreshold_volume_no_candidates"):
        await svc.update_background(
            chain=[{"symbol": "SPY.TEST.C", "strike": 560.0, "volume": 1}],
            spot=560.0,
            atm_iv=0.2,
            limit=5,
        )

    diag = svc.get_diagnostics()
    assert diag["halted"] is True
    assert diag["strict_no_fallback"] is True
    assert "empty_filter_fallback_count" not in diag
    assert "partial_fallback_count" not in diag
    assert "engine_empty_output_fallback_count" not in diag


@pytest.mark.asyncio
async def test_update_background_rejects_when_service_already_halted() -> None:
    svc = _build_service_stub()
    svc._halted = True
    svc._halt_reason = "subthreshold_volume_no_candidates"
    svc._halted_at_utc = "2026-04-03T10:30:00+00:00"

    with pytest.raises(ActiveOptionsHardFailure, match="service_halted"):
        await svc.update_background(
            chain=[{"symbol": "SPY.TEST.C", "strike": 560.0, "volume": 1}],
            spot=560.0,
            atm_iv=0.2,
            limit=5,
        )
