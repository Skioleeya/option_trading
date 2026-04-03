use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList};

pub const FLOW_DIRECTION_VALUES: [&str; 3] = ["BULLISH", "BEARISH", "NEUTRAL"];
pub const FLOW_INTENSITY_VALUES: [&str; 4] = ["EXTREME", "HIGH", "MODERATE", "LOW"];
pub const DIRECTION_COLOR_BULLISH: &str = "text-accent-red";
pub const DIRECTION_COLOR_BEARISH: &str = "text-accent-green";
pub const DIRECTION_COLOR_NEUTRAL: &str = "text-text-secondary";
pub const FLOW_REASON_MISSING_GAMMA: &str = "missing_gamma";
pub const FLOW_REASON_MISSING_VANNA: &str = "missing_vanna";
pub const FLOW_REASON_MISSING_TURNOVER: &str = "missing_turnover";
pub const FLOW_REASON_ALL_ENGINES: &str = "all_engines_inactive";
pub const FLOW_STATE_LIVE: &str = "LIVE";
pub const FLOW_STATE_DEGRADED: &str = "DEGRADED";
pub const ROW_QUALITY_REAL: &str = "REAL";
pub const ROW_QUALITY_SYNTHETIC: &str = "FALLBACK_SYNTHETIC";
pub const ROW_QUALITY_PLACEHOLDER: &str = "PLACEHOLDER";
pub const FALLBACK_REASON_TURNOVER_OI: &str = "turnover_open_interest";
pub const FALLBACK_REASON_HARD_CHAIN: &str = "hard_chain";
pub const FALLBACK_REASON_SUBTHRESHOLD: &str = "subthreshold_volume";
pub const FALLBACK_REASON_ENGINE_EMPTY: &str = "engine_empty_output";
pub const PLACEHOLDER_SIGNATURE_PREFIX: &str = "__placeholder__#";
pub const MAX_CHAIN_VOLUME: i64 = 1_000_000_000;
pub const STRIKE_ROUND_DIGITS: i32 = 4;

pub fn settings_value<T>(py: Python<'_>, name: &str, default: T) -> PyResult<T>
where
    T: for<'a> FromPyObject<'a> + Clone,
{
    let settings = py.import("shared.config")?.getattr("settings")?;
    Ok(settings.getattr(name)?.extract::<T>().unwrap_or(default))
}

pub fn logger(py: Python<'_>) -> PyResult<Bound<'_, PyAny>> {
    Ok(py
        .import("logging")?
        .call_method1("getLogger", ("shared_rust.services.active_options",))?)
}

pub fn as_list<'py>(value: &'py Bound<'py, PyAny>) -> PyResult<Bound<'py, PyList>> {
    value
        .downcast::<PyList>()
        .map_err(|_| PyTypeError::new_err("value must be a list"))
        .cloned()
}

pub fn as_dict<'py>(value: &'py Bound<'py, PyAny>) -> PyResult<Bound<'py, PyDict>> {
    value
        .downcast::<PyDict>()
        .map_err(|_| PyTypeError::new_err("value must be a dict"))
        .cloned()
}

pub fn get_attr_f64(value: &Bound<'_, PyAny>, name: &str) -> f64 {
    value
        .getattr(name)
        .ok()
        .and_then(|raw| raw.extract::<f64>().ok())
        .filter(|num| num.is_finite())
        .unwrap_or(0.0)
}

pub fn get_attr_bool(value: &Bound<'_, PyAny>, name: &str, default: bool) -> bool {
    value
        .getattr(name)
        .ok()
        .and_then(|raw| raw.extract::<bool>().ok())
        .unwrap_or(default)
}

pub fn get_attr_string(value: &Bound<'_, PyAny>, name: &str, default: &str) -> String {
    value
        .getattr(name)
        .ok()
        .and_then(|raw| raw.extract::<String>().ok())
        .unwrap_or_else(|| default.to_string())
}

pub fn round_to(value: f64, digits: i32) -> f64 {
    let factor = 10_f64.powi(digits);
    (value * factor).round() / factor
}

pub fn py_dict_get<'py>(value: &'py Bound<'py, PyDict>, key: &str) -> Option<Bound<'py, PyAny>> {
    value.get_item(key).ok().flatten()
}

pub fn py_to_f64(value: Option<&Bound<'_, PyAny>>) -> f64 {
    value
        .and_then(|raw| raw.extract::<f64>().ok())
        .filter(|num| num.is_finite())
        .unwrap_or(0.0)
}

pub fn py_to_i64(value: Option<&Bound<'_, PyAny>>) -> i64 {
    value
        .and_then(|raw| {
            raw.extract::<i64>().ok().or_else(|| {
                raw.extract::<f64>().ok().and_then(|v| {
                    if v.is_finite() {
                        Some(v.round() as i64)
                    } else {
                        None
                    }
                })
            })
        })
        .unwrap_or(0)
}

pub fn py_to_bool(value: Option<&Bound<'_, PyAny>>, default: bool) -> bool {
    value
        .and_then(|raw| raw.extract::<bool>().ok())
        .unwrap_or(default)
}

pub fn py_to_string(value: Option<&Bound<'_, PyAny>>) -> Option<String> {
    value.and_then(|raw| raw.extract::<String>().ok())
}

pub fn make_flow_component(
    py: Python<'_>,
    symbol: &str,
    strike: f64,
    option_type: &str,
    flow_value: f64,
    is_valid: bool,
    failure_reason: &str,
) -> PyResult<Py<PyAny>> {
    let kwargs = PyDict::new(py);
    kwargs.set_item("symbol", symbol)?;
    kwargs.set_item("strike", strike)?;
    kwargs.set_item("option_type", option_type)?;
    kwargs.set_item("flow_value", flow_value)?;
    kwargs.set_item("is_valid", is_valid)?;
    kwargs.set_item("failure_reason", failure_reason)?;
    Ok(py
        .import("shared_rust.models")?
        .getattr("FlowComponentResult")?
        .call((), Some(&kwargs))?
        .unbind())
}

pub fn make_flow_output(py: Python<'_>, fields: &[(&str, Bound<'_, PyAny>)]) -> PyResult<Py<PyAny>> {
    let kwargs = PyDict::new(py);
    for (key, value) in fields {
        kwargs.set_item(*key, value)?;
    }
    Ok(py
        .import("shared_rust.models")?
        .getattr("FlowEngineOutput")?
        .call((), Some(&kwargs))?
        .unbind())
}
