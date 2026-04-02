"""Rust-backed helpers for L0 runtime quote profile and contract surfaces."""

from __future__ import annotations

from typing import Any

from shared.services.l0_runtime.native_loader import l0_rust

# Reuse the package-managed extension module instance to keep Python/Rust types coherent.
_L0_RUST = l0_rust


def build_endpoint_profiles_native(
    *,
    http_url: str | None,
    quote_ws_url: str | None,
    trade_ws_url: str | None,
) -> list[dict[str, str]]:
    return list(
        _L0_RUST.quote_api_build_endpoint_profiles(
            http_url,
            quote_ws_url,
            trade_ws_url,
        )
    )


def build_gateway_config_native(
    *,
    app_key: str,
    app_secret: str,
    access_token: str,
    http_url: str | None,
    quote_ws_url: str | None,
    trade_ws_url: str | None,
    language: str | None,
    enable_overnight: bool,
) -> dict[str, Any]:
    return dict(
        _L0_RUST.quote_api_build_gateway_config(
            app_key,
            app_secret,
            access_token,
            http_url,
            quote_ws_url,
            trade_ws_url,
            language,
            enable_overnight,
        )
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
