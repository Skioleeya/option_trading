from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from l3_assembly.assembly.payload_assembler import PayloadAssemblerV2
from l3_assembly.events.payload_events import UIState


def _decision(version: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        signal="NEUTRAL",
        direction="NEUTRAL",
        confidence=0.0,
        pre_guard_direction="NEUTRAL",
        guard_actions=(),
        signal_summary={},
        fusion_weights={},
        latency_ms=0.0,
        version=version,
        computed_at=datetime.now(timezone.utc),
        data={},
    )


def _snapshot(*, zero_gamma_level: float, flip_level_cumulative: float) -> dict[str, float | str]:
    return {
        "spot": 679.87,
        "as_of": "2026-04-13T15:24:32.426386+00:00",
        "atm_iv": 0.1047,
        "net_gex": 739.71,
        "call_wall": 685.0,
        "put_wall": 675.0,
        "flip_level": flip_level_cumulative,
        "flip_level_cumulative": flip_level_cumulative,
        "zero_gamma_level": zero_gamma_level,
    }


def test_assemble_uses_zero_gamma_for_payload_and_depth_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, float | None] = {}

    def _fake_build_ui_state(
        self: PayloadAssemblerV2,
        snap: object,
        active_options: object,
        *,
        flip_level: float | None,
    ) -> UIState:
        captured["flip_level"] = flip_level
        return UIState.zero_state()

    monkeypatch.setattr(PayloadAssemblerV2, "_build_ui_state", _fake_build_ui_state)
    payload = PayloadAssemblerV2().assemble(
        _decision(version=101),
        _snapshot(zero_gamma_level=678.97, flip_level_cumulative=686.0),
        atm_decay=None,
    )

    assert payload.gamma_flip_level == pytest.approx(678.97)
    assert captured["flip_level"] == pytest.approx(678.97)
    assert payload.to_dict()["agent_g"]["data"]["gamma_flip_level"] == pytest.approx(678.97)


def test_assemble_does_not_fallback_to_cumulative_when_zero_gamma_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, float | None] = {}

    def _fake_build_ui_state(
        self: PayloadAssemblerV2,
        snap: object,
        active_options: object,
        *,
        flip_level: float | None,
    ) -> UIState:
        captured["flip_level"] = flip_level
        return UIState.zero_state()

    monkeypatch.setattr(PayloadAssemblerV2, "_build_ui_state", _fake_build_ui_state)
    payload = PayloadAssemblerV2().assemble(
        _decision(version=102),
        _snapshot(zero_gamma_level=0.0, flip_level_cumulative=686.0),
        atm_decay=None,
    )

    assert payload.gamma_flip_level is None
    assert captured["flip_level"] is None
    assert payload.to_dict()["agent_g"]["data"]["gamma_flip_level"] is None


def test_assemble_rejects_non_finite_zero_gamma_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, float | None] = {}

    def _fake_build_ui_state(
        self: PayloadAssemblerV2,
        snap: object,
        active_options: object,
        *,
        flip_level: float | None,
    ) -> UIState:
        captured["flip_level"] = flip_level
        return UIState.zero_state()

    monkeypatch.setattr(PayloadAssemblerV2, "_build_ui_state", _fake_build_ui_state)
    payload = PayloadAssemblerV2().assemble(
        _decision(version=103),
        _snapshot(zero_gamma_level=float("nan"), flip_level_cumulative=686.0),
        atm_decay=None,
    )

    assert payload.gamma_flip_level is None
    assert captured["flip_level"] is None
    assert payload.to_dict()["agent_g"]["data"]["gamma_flip_level"] is None
