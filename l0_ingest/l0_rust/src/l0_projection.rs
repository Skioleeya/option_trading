use crate::transport_contract::{
    DEFAULT_SHM_HEAD, DEFAULT_SHM_TAIL, SHM_STATUS_DISCONNECTED, SHM_STATUS_ERROR,
    SHM_STATUS_UNINITIALIZED,
};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};

fn dict_or_empty<'py>(py: Python<'py>, value: Option<Bound<'py, PyAny>>) -> PyResult<Bound<'py, PyDict>> {
    match value {
        Some(inner) => Ok(inner.downcast_into::<PyDict>()?),
        None => Ok(PyDict::new(py)),
    }
}

#[pyfunction]
fn l0_projection_build_uninitialized_snapshot(py: Python<'_>, version: i64) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("spot", py.None())?;
    out.set_item("chain", Vec::<i32>::new())?;
    out.set_item("as_of", py.None())?;
    out.set_item("as_of_utc", py.None())?;
    out.set_item("version", version)?;
    out.set_item("rust_active", false)?;
    out.set_item("rust_shm_path", py.None())?;
    let shm_stats = PyDict::new(py);
    shm_stats.set_item("head", DEFAULT_SHM_HEAD)?;
    shm_stats.set_item("tail", DEFAULT_SHM_TAIL)?;
    shm_stats.set_item("status", SHM_STATUS_UNINITIALIZED)?;
    out.set_item("shm_stats", shm_stats)?;
    Ok(out.unbind())
}

#[pyfunction]
#[pyo3(signature = (spot, version, now, now_utc_iso))]
fn l0_projection_build_error_snapshot(
    py: Python<'_>,
    spot: Option<f64>,
    version: i64,
    now: Bound<'_, PyAny>,
    now_utc_iso: String,
) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("spot", spot)?;
    out.set_item("chain", Vec::<i32>::new())?;
    out.set_item("as_of", now)?;
    out.set_item("as_of_utc", now_utc_iso)?;
    out.set_item("version", version)?;
    out.set_item("rust_active", false)?;
    out.set_item("rust_shm_path", py.None())?;
    let shm_stats = PyDict::new(py);
    shm_stats.set_item("head", DEFAULT_SHM_HEAD)?;
    shm_stats.set_item("tail", DEFAULT_SHM_TAIL)?;
    shm_stats.set_item("status", SHM_STATUS_ERROR)?;
    out.set_item("shm_stats", shm_stats)?;
    Ok(out.unbind())
}

#[pyfunction]
#[pyo3(signature = (rust_active, rust_shm_path=None, shm_stats=None))]
fn l0_projection_build_runtime_status(
    py: Python<'_>,
    rust_active: bool,
    rust_shm_path: Option<String>,
    shm_stats: Option<Bound<'_, PyAny>>,
) -> PyResult<Py<PyDict>> {
    let stats = dict_or_empty(py, shm_stats)?;
    let head = stats
        .get_item("head")?
        .and_then(|value| value.extract::<Option<u64>>().ok())
        .flatten()
        .unwrap_or(DEFAULT_SHM_HEAD);
    let tail = stats
        .get_item("tail")?
        .and_then(|value| value.extract::<Option<u64>>().ok())
        .flatten()
        .unwrap_or(DEFAULT_SHM_TAIL);
    let status = stats
        .get_item("status")?
        .and_then(|value| value.extract::<Option<String>>().ok())
        .flatten()
        .unwrap_or_else(|| SHM_STATUS_DISCONNECTED.to_string());
    let status_dict = PyDict::new(py);
    status_dict.set_item("head", head)?;
    status_dict.set_item("tail", tail)?;
    status_dict.set_item("status", status)?;

    let out = PyDict::new(py);
    out.set_item("rust_active", rust_active)?;
    out.set_item("rust_shm_path", if rust_active { rust_shm_path } else { None::<String> })?;
    out.set_item("shm_stats", status_dict)?;
    Ok(out.unbind())
}

#[pyfunction]
fn l0_projection_build_governor_telemetry(
    py: Python<'_>,
    symbols_per_min: u64,
    cooldown_active: bool,
    limiter_profile: String,
    cooldown_hits_5m: u64,
    warmup_pending_symbols: u64,
    metadata_cache_hit_rate: f64,
) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("symbols_per_min", symbols_per_min)?;
    out.set_item("cooldown_active", cooldown_active)?;
    out.set_item("limiter_profile", limiter_profile)?;
    out.set_item("cooldown_hits_5m", cooldown_hits_5m)?;
    out.set_item("warmup_pending_symbols", warmup_pending_symbols)?;
    out.set_item("metadata_cache_hit_rate", metadata_cache_hit_rate)?;
    Ok(out.unbind())
}

#[pyfunction]
#[pyo3(signature = (
    spot,
    chain,
    version,
    tier2_chain,
    tier3_chain,
    volume_map,
    aggregate_greeks,
    ttm_seconds,
    now,
    now_utc_iso,
    runtime_status,
    governor_telemetry,
    official_hv_diagnostics,
    header_volatility_aux_diagnostics,
    chain_arrow=None
))]
fn l0_projection_compose_fetch_chain_payload(
    py: Python<'_>,
    spot: Option<f64>,
    chain: Bound<'_, PyAny>,
    version: i64,
    tier2_chain: Bound<'_, PyAny>,
    tier3_chain: Bound<'_, PyAny>,
    volume_map: Bound<'_, PyAny>,
    aggregate_greeks: Bound<'_, PyAny>,
    ttm_seconds: f64,
    now: Bound<'_, PyAny>,
    now_utc_iso: String,
    runtime_status: Bound<'_, PyAny>,
    governor_telemetry: Bound<'_, PyAny>,
    official_hv_diagnostics: Bound<'_, PyAny>,
    header_volatility_aux_diagnostics: Bound<'_, PyAny>,
    chain_arrow: Option<Bound<'_, PyAny>>,
) -> PyResult<Py<PyDict>> {
    let runtime = runtime_status.downcast_into::<PyDict>()?;
    let out = PyDict::new(py);
    out.set_item("spot", spot)?;
    out.set_item("chain", chain)?;
    out.set_item("version", version)?;
    out.set_item("tier2_chain", tier2_chain)?;
    out.set_item("tier3_chain", tier3_chain)?;
    out.set_item("volume_map", volume_map)?;
    out.set_item("aggregate_greeks", aggregate_greeks)?;
    out.set_item("ttm_seconds", ttm_seconds)?;
    out.set_item("as_of", now)?;
    out.set_item("as_of_utc", now_utc_iso)?;
    out.set_item(
        "rust_active",
        runtime
            .get_item("rust_active")?
            .unwrap_or(py.None().bind(py).clone())
            .extract::<bool>()?,
    )?;
    out.set_item("rust_shm_path", runtime.get_item("rust_shm_path")?.unwrap_or(py.None().bind(py).clone()))?;
    out.set_item("shm_stats", runtime.get_item("shm_stats")?.unwrap_or(py.None().bind(py).clone()))?;
    out.set_item("governor_telemetry", governor_telemetry)?;
    out.set_item("official_hv_diagnostics", official_hv_diagnostics)?;
    out.set_item("header_volatility_aux_diagnostics", header_volatility_aux_diagnostics)?;
    if let Some(batch) = chain_arrow {
        out.set_item("chain_arrow", batch)?;
    }
    Ok(out.unbind())
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(l0_projection_build_uninitialized_snapshot, module)?)?;
    module.add_function(wrap_pyfunction!(l0_projection_build_error_snapshot, module)?)?;
    module.add_function(wrap_pyfunction!(l0_projection_build_runtime_status, module)?)?;
    module.add_function(wrap_pyfunction!(l0_projection_build_governor_telemetry, module)?)?;
    module.add_function(wrap_pyfunction!(l0_projection_compose_fetch_chain_payload, module)?)?;
    Ok(())
}
