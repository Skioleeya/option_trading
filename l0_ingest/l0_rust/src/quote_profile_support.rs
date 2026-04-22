use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyModule};

const DEFAULT_HTTP_URL: &str = "https://openapi.longportapp.com";
const DEFAULT_QUOTE_WS_URL: &str = "wss://openapi-quote.longportapp.com/v2";
const DEFAULT_TRADE_WS_URL: &str = "wss://openapi-trade.longportapp.com/v2";
const LEGACY_HTTP_URL: &str = "https://openapi.longbridge.com";
const LEGACY_QUOTE_WS_URL: &str = "wss://openapi-quote.longbridge.com/v2";
const LEGACY_TRADE_WS_URL: &str = "wss://openapi-trade.longbridge.com/v2";

fn clean_text(value: Option<String>) -> Option<String> {
    value.map(|text| text.trim().to_string()).filter(|text| !text.is_empty())
}

fn convert_gateway(value: &str, src_host: &str, dst_host: &str) -> String {
    value.replace(src_host, dst_host)
}

fn push_profile(
    out: &Bound<'_, PyList>,
    seen: &mut std::collections::HashSet<(String, String, String)>,
    name: &str,
    http_url: String,
    quote_ws_url: String,
    trade_ws_url: String,
) -> PyResult<()> {
    let key = (http_url.clone(), quote_ws_url.clone(), trade_ws_url.clone());
    if seen.contains(&key) {
        return Ok(());
    }
    seen.insert(key);
    let profile = PyDict::new(out.py());
    profile.set_item("name", name)?;
    profile.set_item("http_url", http_url)?;
    profile.set_item("quote_ws_url", quote_ws_url)?;
    profile.set_item("trade_ws_url", trade_ws_url)?;
    out.append(profile)?;
    Ok(())
}

#[pyfunction]
#[pyo3(signature = (http_url=None, quote_ws_url=None, trade_ws_url=None))]
fn quote_api_build_endpoint_profiles(
    py: Python<'_>,
    http_url: Option<String>,
    quote_ws_url: Option<String>,
    trade_ws_url: Option<String>,
) -> PyResult<Py<PyList>> {
    let primary_http = clean_text(http_url).unwrap_or_else(|| DEFAULT_HTTP_URL.to_string());
    let primary_quote_ws = clean_text(quote_ws_url).unwrap_or_else(|| DEFAULT_QUOTE_WS_URL.to_string());
    let primary_trade_ws = clean_text(trade_ws_url).unwrap_or_else(|| DEFAULT_TRADE_WS_URL.to_string());
    let out = PyList::empty(py);
    let mut seen = std::collections::HashSet::new();
    push_profile(
        &out,
        &mut seen,
        "primary",
        primary_http.clone(),
        primary_quote_ws.clone(),
        primary_trade_ws.clone(),
    )?;

    if primary_http.contains("longbridge.com") {
        push_profile(
            &out,
            &mut seen,
            "official_longportapp",
            convert_gateway(&primary_http, "openapi.longbridge.com", "openapi.longportapp.com"),
            convert_gateway(&primary_quote_ws, "openapi-quote.longbridge.com", "openapi-quote.longportapp.com"),
            convert_gateway(&primary_trade_ws, "openapi-trade.longbridge.com", "openapi-trade.longportapp.com"),
        )?;
    } else if primary_http.contains("longportapp.com") {
        push_profile(
            &out,
            &mut seen,
            "official_longbridge",
            convert_gateway(&primary_http, "openapi.longportapp.com", "openapi.longbridge.com"),
            convert_gateway(&primary_quote_ws, "openapi-quote.longportapp.com", "openapi-quote.longbridge.com"),
            convert_gateway(&primary_trade_ws, "openapi-trade.longportapp.com", "openapi-trade.longbridge.com"),
        )?;
    } else {
        push_profile(
            &out,
            &mut seen,
            "official_longportapp",
            DEFAULT_HTTP_URL.to_string(),
            DEFAULT_QUOTE_WS_URL.to_string(),
            DEFAULT_TRADE_WS_URL.to_string(),
        )?;
        push_profile(
            &out,
            &mut seen,
            "official_longbridge",
            LEGACY_HTTP_URL.to_string(),
            LEGACY_QUOTE_WS_URL.to_string(),
            LEGACY_TRADE_WS_URL.to_string(),
        )?;
    }
    Ok(out.unbind())
}

#[pyfunction]
#[pyo3(signature = (app_key, app_secret, access_token, http_url=None, quote_ws_url=None, trade_ws_url=None, language=None, enable_overnight=false))]
fn quote_api_build_gateway_config(
    py: Python<'_>,
    app_key: String,
    app_secret: String,
    access_token: String,
    http_url: Option<String>,
    quote_ws_url: Option<String>,
    trade_ws_url: Option<String>,
    language: Option<String>,
    enable_overnight: bool,
) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("app_key", app_key)?;
    out.set_item("app_secret", app_secret)?;
    out.set_item("access_token", access_token)?;
    out.set_item("http_url", clean_text(http_url))?;
    out.set_item("quote_ws_url", clean_text(quote_ws_url))?;
    out.set_item("trade_ws_url", clean_text(trade_ws_url))?;
    out.set_item("language", clean_text(language).unwrap_or_else(|| "EN".to_string()).replace('-', "_").to_ascii_uppercase())?;
    out.set_item("enable_overnight", enable_overnight)?;
    Ok(out.unbind())
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(quote_api_build_endpoint_profiles, module)?)?;
    module.add_function(wrap_pyfunction!(quote_api_build_gateway_config, module)?)?;
    Ok(())
}
