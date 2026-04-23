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
    svc._empty_filter_count = 0
    svc._last_empty_filter_at_utc = None
    svc._last_filtered_candidates_count = 0
    svc._last_update_at_utc = None
    svc._last_input_chain_size = 0
    svc._last_input_day_volume_gt_zero = 0
    svc._last_input_current_volume_gt_zero = 0
    svc._last_input_turnover_gt_zero = 0
    svc._last_input_gamma_nonzero = 0
    svc._spot_window_steps = 7
    svc._latest_source_version = 0
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
        staticmethod(lambda *, chain, spot, spot_window_steps: []),
    )

    with pytest.raises(ActiveOptionsHardFailure, match="normalized_chain_empty_no_candidates"):
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
    svc._halt_reason = "normalized_chain_empty_no_candidates"
    svc._halted_at_utc = "2026-04-03T10:30:00+00:00"

    with pytest.raises(ActiveOptionsHardFailure, match="service_halted"):
        await svc.update_background(
            chain=[{"symbol": "SPY.TEST.C", "strike": 560.0, "volume": 0, "turnover": 0.0}],
            spot=560.0,
            atm_iv=0.2,
            limit=5,
        )


@pytest.mark.asyncio
async def test_update_background_rearms_when_traded_volume_returns_after_engine_empty_output() -> None:
    svc = _build_service_stub()
    svc._halted = True
    svc._halt_reason = "engine_empty_output"
    svc._halted_at_utc = "2026-04-23T13:24:51+00:00"

    async def _noop_save(*, redis, filtered) -> None:
        return None

    async def _fake_run_pipeline(*, filtered, spot, atm_iv, gex_regime, ttm_seconds, redis):
        return [{"symbol": "SPY260423C709000.US"}]

    svc._normalize_and_filter_chain = lambda *, chain, spot, spot_window_steps: [dict(chain[0])]  # type: ignore[assignment]
    svc._save_oi_snapshot_if_enabled = _noop_save  # type: ignore[assignment]
    svc._run_flow_pipeline = _fake_run_pipeline  # type: ignore[assignment]
    svc._build_ranked_candidate = lambda outputs, limit: (  # type: ignore[assignment]
        [
            {
                "symbol": "SPY",
                "option_type": "CALL",
                "strike": 709.0,
                "volume": 25,
                "turnover": 12500.0,
            }
        ],
        (("SPY260423C709000.US", "CALL", 709.0),),
    )

    await svc.update_background(
        chain=[{"symbol": "SPY260423C709000.US", "strike": 709.0, "volume": 25, "turnover": 12500.0}],
        spot=709.0,
        atm_iv=0.2,
        limit=5,
    )

    assert svc.get_diagnostics()["halted"] is False
    assert svc.get_latest()[0]["strike"] == 709.0
    assert svc.get_latest()[0]["volume"] == 25


@pytest.mark.asyncio
async def test_update_background_commits_new_signature_each_tick() -> None:
    svc = _build_service_stub()

    async def _noop_save(*, redis, filtered) -> None:
        return None

    async def _fake_run_pipeline(*, filtered, spot, atm_iv, gex_regime, ttm_seconds, redis):
        return [{"symbol": "unused"}]

    ranked = [
        (
            [{"symbol": "SPY", "option_type": "CALL", "strike": 680.0, "volume": 10, "turnover": 1000.0}],
            (("SPY260413C680000.US", "CALL", 680.0),),
        ),
        (
            [{"symbol": "SPY", "option_type": "CALL", "strike": 686.0, "volume": 20, "turnover": 2000.0}],
            (("SPY260413C686000.US", "CALL", 686.0),),
        ),
    ]

    svc._normalize_and_filter_chain = lambda *, chain, spot, spot_window_steps: [dict(chain[0])]  # type: ignore[assignment]
    svc._save_oi_snapshot_if_enabled = _noop_save  # type: ignore[assignment]
    svc._run_flow_pipeline = _fake_run_pipeline  # type: ignore[assignment]
    svc._build_ranked_candidate = lambda outputs, limit: ranked.pop(0)  # type: ignore[assignment]

    base_chain = [{"symbol": "SPY260413C680000.US", "strike": 680.0, "volume": 1, "turnover": 1.0}]

    await svc.update_background(chain=base_chain, spot=680.0, atm_iv=0.2, limit=5)
    assert svc.get_latest()[0]["strike"] == 680.0
    assert svc.get_latest()[0]["volume"] == 10

    await svc.update_background(chain=base_chain, spot=680.0, atm_iv=0.2, limit=5)
    assert svc.get_latest()[0]["strike"] == 686.0
    assert svc.get_latest()[0]["volume"] == 20
