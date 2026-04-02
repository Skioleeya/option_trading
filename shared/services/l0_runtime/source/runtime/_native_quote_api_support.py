"""Rust-backed helpers for L0 quote API contract normalization."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.services.l0_runtime._native_extension_loader import load_l0_rust

_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "_native_generated"
_L0_RUST = load_l0_rust(
    candidates=[
        _PACKAGE_DIR / "wave6" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave5" / "l0_rust.pyd",
        _PACKAGE_DIR / "wave4" / "l0_rust.pyd",
        _PACKAGE_DIR / "l0_rust.pyd",
    ],
    module_suffix="l0_rust_wave6_quote_api",
)


def build_option_quote_contract_native(row: Any) -> dict[str, Any]:
    return dict(_L0_RUST.quote_api_build_option_quote_contract(row))


def build_option_chain_strike_contract_native(row: Any) -> dict[str, Any]:
    return dict(_L0_RUST.quote_api_build_option_chain_strike_contract(row))


def build_calc_index_contract_native(row: Any) -> dict[str, Any]:
    return dict(_L0_RUST.quote_api_build_calc_index_contract(row))


def rest_quote_rows_native(gateway: Any, symbols: list[str]) -> list[dict[str, Any]]:
    rows_fn = getattr(gateway, "rest_quote_rows", None)
    if callable(rows_fn):
        return list(rows_fn(symbols))
    return list(_L0_RUST.quote_api_rest_quote_rows(gateway, symbols))


def rest_option_quote_contracts_native(
    gateway: Any,
    symbols: list[str],
) -> list[dict[str, Any]]:
    rows_fn = getattr(gateway, "rest_option_quote_contracts", None)
    if callable(rows_fn):
        return [build_option_quote_contract_native(row) for row in rows_fn(symbols)]
    return list(_L0_RUST.quote_api_rest_option_quote_contracts(gateway, symbols))


def rest_option_chain_info_by_date_contracts_native(
    gateway: Any,
    symbol: str,
    expiry_iso: str,
) -> list[dict[str, Any]]:
    rows_fn = getattr(gateway, "rest_option_chain_info_by_date_contracts", None)
    if callable(rows_fn):
        return [build_option_chain_strike_contract_native(row) for row in rows_fn(symbol, expiry_iso)]
    return list(_L0_RUST.quote_api_rest_option_chain_info_by_date_contracts(gateway, symbol, expiry_iso))


def rest_calc_indexes_contracts_native(
    gateway: Any,
    symbols: list[str],
    indexes: list[str],
) -> list[dict[str, Any]]:
    rows_fn = getattr(gateway, "rest_calc_indexes_contracts", None)
    if callable(rows_fn):
        return [build_calc_index_contract_native(row) for row in rows_fn(symbols, indexes)]
    return list(_L0_RUST.quote_api_rest_calc_indexes_contracts(gateway, symbols, indexes))
