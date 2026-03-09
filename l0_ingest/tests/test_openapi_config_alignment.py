from __future__ import annotations

from types import SimpleNamespace

import pytest
from longport.openapi import Language

from l0_ingest.feeds.option_chain_builder import (
    _build_openapi_endpoint_profiles,
    _longport_config_kwargs,
    _startup_connectivity_probe,
    _sync_openapi_env_aliases,
)


def _cfg() -> SimpleNamespace:
    return SimpleNamespace(
        longport_app_key="k",
        longport_app_secret="s",
        longport_access_token="t",
        longport_http_url="https://openapi.longportapp.com",
        longport_quote_ws_url="wss://openapi-quote.longportapp.com/v2",
        longport_trade_ws_url="wss://openapi-trade.longportapp.com/v2",
        longport_language="en",
        longport_enable_overnight=True,
        longport_startup_strict_connectivity=True,
    )


def test_longport_config_kwargs_include_official_gateway_fields() -> None:
    kwargs = _longport_config_kwargs(_cfg())
    assert kwargs["app_key"] == "k"
    assert kwargs["app_secret"] == "s"
    assert kwargs["access_token"] == "t"
    assert kwargs["http_url"] == "https://openapi.longportapp.com"
    assert kwargs["quote_ws_url"] == "wss://openapi-quote.longportapp.com/v2"
    assert kwargs["trade_ws_url"] == "wss://openapi-trade.longportapp.com/v2"
    assert kwargs["language"] == Language.EN
    assert kwargs["enable_overnight"] is True


def test_longport_config_kwargs_normalize_language_aliases() -> None:
    cfg = _cfg()
    cfg.longport_language = "zh_CN"
    kwargs = _longport_config_kwargs(cfg)
    assert kwargs["language"] == Language.ZH_CN


def test_longport_config_kwargs_unknown_language_fallback_to_en() -> None:
    cfg = _cfg()
    cfg.longport_language = "jp"
    kwargs = _longport_config_kwargs(cfg)
    assert kwargs["language"] == Language.EN


def test_sync_openapi_env_aliases_sets_longport_and_longbridge(monkeypatch) -> None:
    for key in (
        "LONGPORT_APP_KEY",
        "LONGBRIDGE_APP_KEY",
        "LONGPORT_HTTP_URL",
        "LONGBRIDGE_HTTP_URL",
        "LONGPORT_ENABLE_OVERNIGHT",
        "LONGBRIDGE_ENABLE_OVERNIGHT",
        "LONGPORT_STARTUP_STRICT_CONNECTIVITY",
        "LONGBRIDGE_STARTUP_STRICT_CONNECTIVITY",
    ):
        monkeypatch.delenv(key, raising=False)

    applied = _sync_openapi_env_aliases(_cfg())
    assert applied["LONGPORT_APP_KEY"] == "k"
    assert applied["LONGBRIDGE_APP_KEY"] == "k"
    assert applied["LONGPORT_HTTP_URL"] == "https://openapi.longportapp.com"
    assert applied["LONGBRIDGE_HTTP_URL"] == "https://openapi.longportapp.com"
    assert applied["LONGPORT_ENABLE_OVERNIGHT"] == "true"
    assert applied["LONGBRIDGE_ENABLE_OVERNIGHT"] == "true"
    assert applied["LONGPORT_STARTUP_STRICT_CONNECTIVITY"] == "true"
    assert applied["LONGBRIDGE_STARTUP_STRICT_CONNECTIVITY"] == "true"


def test_build_openapi_endpoint_profiles_adds_official_longbridge_fallback() -> None:
    profiles = _build_openapi_endpoint_profiles(_cfg())
    assert len(profiles) == 2
    assert profiles[0]["name"] == "primary"
    assert profiles[0]["http_url"] == "https://openapi.longportapp.com"
    assert profiles[1]["name"] == "official_longbridge"
    assert profiles[1]["http_url"] == "https://openapi.longbridge.com"


def test_build_openapi_endpoint_profiles_dedupes_duplicate_profiles() -> None:
    cfg = _cfg()
    cfg.longport_http_url = "https://openapi.longbridge.com"
    cfg.longport_quote_ws_url = "wss://openapi-quote.longbridge.com/v2"
    cfg.longport_trade_ws_url = "wss://openapi-trade.longbridge.com/v2"

    profiles = _build_openapi_endpoint_profiles(cfg)
    assert len(profiles) == 2
    assert profiles[0]["name"] == "primary"
    assert profiles[1]["name"] == "official_longportapp"


class _ProbeRuntime:
    def __init__(self, fail: bool) -> None:
        self._fail = fail

    async def quote(self, _symbols: list[str]):
        if self._fail:
            raise RuntimeError("socket/token connect failed")
        return [SimpleNamespace(symbol="SPY.US")]

    def diagnostics(self) -> dict[str, str]:
        return {
            "endpoint_profile": "primary",
            "endpoint_http_url": "https://openapi.longportapp.com",
        }


@pytest.mark.asyncio
async def test_startup_connectivity_probe_raises_in_strict_mode() -> None:
    runtime = _ProbeRuntime(fail=True)
    with pytest.raises(RuntimeError, match="startup connectivity probe failed"):
        await _startup_connectivity_probe(runtime, strict_connectivity=True)


@pytest.mark.asyncio
async def test_startup_connectivity_probe_allows_degraded_when_strict_disabled() -> None:
    runtime = _ProbeRuntime(fail=True)
    await _startup_connectivity_probe(runtime, strict_connectivity=False)
