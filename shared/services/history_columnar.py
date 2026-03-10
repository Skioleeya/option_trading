"""Shared helpers for non-breaking history columnar schema v2 payloads."""

from __future__ import annotations

from typing import Any, Mapping


COLUMNAR_SCHEMA_VERSION = "v2"
COLUMNAR_ENCODING = "columnar-json"


def pack_rows_columnar(rows: list[Mapping[str, Any]]) -> tuple[list[str], list[list[Any]]]:
    """Encode row-oriented objects into a columnar matrix.

    Columns are discovered by first-seen key order across rows, preserving
    deterministic output for a given input sequence.
    """
    if not rows:
        return [], []

    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                columns.append(key)

    matrix: list[list[Any]] = []
    for row in rows:
        matrix.append([row.get(col) for col in columns])
    return columns, matrix


def build_columnar_payload(
    rows: list[Mapping[str, Any]],
    *,
    count: int | None = None,
    meta: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a schema=v2 payload envelope from row objects."""
    columns, matrix = pack_rows_columnar(rows)
    payload: dict[str, Any] = {
        "schema": COLUMNAR_SCHEMA_VERSION,
        "encoding": COLUMNAR_ENCODING,
        "columns": columns,
        "rows": matrix,
        "count": int(count if count is not None else len(rows)),
    }
    if meta:
        payload.update(dict(meta))
    return payload
