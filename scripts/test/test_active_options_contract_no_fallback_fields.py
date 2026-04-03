from __future__ import annotations

from l3_assembly.events.active_options_contract import active_option_row_from_dict


def test_active_option_contract_drops_fallback_fields() -> None:
    row = active_option_row_from_dict(
        {
            "symbol": "SPY260319C00560000.US",
            "option_type": "CALL",
            "strike": 560.0,
            "implied_volatility": 0.22,
            "volume": 123,
            "turnover": 100000.0,
            "flow": 120000.0,
            "flow_score": 1.2,
            "impact_index": 2.1,
            "is_sweep": False,
            "flow_deg_formatted": "$120K",
            "flow_volume_label": "120K",
            "flow_color": "text-bullish",
            "flow_glow": "shadow-bullish",
            "flow_intensity": "HIGH",
            "flow_direction": "BULLISH",
            "flow_d_z": 1.0,
            "flow_e_z": 0.8,
            "flow_g_z": 0.6,
            "is_placeholder": False,
            "slot_index": 1,
            "row_quality": "REAL",
            "fallback_reason": "engine_empty_output",
            "is_synthetic_fallback": True,
            "flow_signal_state": "LIVE",
        }
    )

    payload = row.to_dict()
    assert "fallback_reason" not in payload
    assert "is_synthetic_fallback" not in payload
