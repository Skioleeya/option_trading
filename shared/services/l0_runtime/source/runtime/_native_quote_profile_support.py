"""Rust-backed helpers for quote endpoint/profile configuration."""

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
    module_suffix="l0_rust_wave6_quote_profile",
)


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
