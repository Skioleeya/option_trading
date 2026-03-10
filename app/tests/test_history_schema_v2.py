from __future__ import annotations

from app.routes.history import _parse_schema, _project_fields
from shared.config import settings
from shared.services.history_columnar import build_columnar_payload, pack_rows_columnar


def _decode_columnar(payload: dict[str, object]) -> list[dict[str, object]]:
    columns = payload.get("columns", [])
    rows = payload.get("rows", [])
    assert isinstance(columns, list)
    assert isinstance(rows, list)
    out: list[dict[str, object]] = []
    for row in rows:
        assert isinstance(row, list)
        out.append({str(columns[i]): row[i] if i < len(row) else None for i in range(len(columns))})
    return out


def test_pack_rows_columnar_empty():
    cols, matrix = pack_rows_columnar([])
    assert cols == []
    assert matrix == []


def test_pack_rows_columnar_preserves_first_seen_column_order():
    rows = [
        {"timestamp": "t1", "spot": 100.0},
        {"timestamp": "t2", "direction": "BULLISH", "spot": 101.0},
    ]
    cols, matrix = pack_rows_columnar(rows)
    assert cols == ["timestamp", "spot", "direction"]
    assert matrix == [["t1", 100.0, None], ["t2", 101.0, "BULLISH"]]


def test_build_columnar_payload_roundtrip_after_projection():
    rows = [
        {"timestamp": "t1", "straddle_pct": 0.01, "call_pct": 0.006, "put_pct": 0.004},
        {"timestamp": "t2", "straddle_pct": 0.02, "call_pct": 0.009, "put_pct": 0.011},
    ]
    projected = _project_fields(rows, ["timestamp", "straddle_pct", "put_pct"])
    payload = build_columnar_payload(projected, count=len(projected), meta={"view": "compact"})
    decoded = _decode_columnar(payload)
    assert payload["schema"] == "v2"
    assert payload["encoding"] == "columnar-json"
    assert payload["count"] == 2
    assert payload["view"] == "compact"
    assert decoded == projected


def test_parse_schema_rejects_invalid():
    try:
        _parse_schema("v9")
        assert False, "expected invalid schema to raise"
    except Exception as exc:
        assert "invalid schema" in str(exc)


def test_parse_schema_falls_back_to_v1_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "history_v2_enabled", False, raising=False)
    assert _parse_schema("v2") == "v1"
    monkeypatch.setattr(settings, "history_v2_enabled", True, raising=False)


def test_parse_schema_uses_config_default_when_missing(monkeypatch):
    monkeypatch.setattr(settings, "history_schema_default", "v2", raising=False)
    assert _parse_schema(None) == "v2"
