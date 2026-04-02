use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};

pub const L0_IPC_SIGNAL_ENV_KEY: &str = "L0_IPC_SIGNAL_NAME";
pub const L0_BATCH_INTERVAL_ENV_KEY: &str = "L0_BATCH_INTERVAL_MS";
pub const L0_BATCH_MAX_ROWS_ENV_KEY: &str = "L0_BATCH_MAX_ROWS";
pub const L0_IPC_SHM_BYTES_ENV_KEY: &str = "L0_IPC_SHM_BYTES";
pub const L0_ARROW_SIGNAL_SUFFIX: &str = "_signal";
pub const DEFAULT_L0_BATCH_INTERVAL_MS: u64 = 50;
pub const DEFAULT_L0_BATCH_MAX_ROWS: usize = 256;
pub const DEFAULT_L0_IPC_SHM_BYTES: usize = 0;
pub const DEFAULT_LONGPORT_CONNECT_RETRIES: u64 = 3;
pub const DEFAULT_LONGPORT_CONNECT_RETRY_BASE_SEC: f64 = 0.8;
pub const DEFAULT_SHM_HEAD: u64 = 0;
pub const DEFAULT_SHM_TAIL: u64 = 0;
pub const SHM_STATUS_OK: &str = "OK";
pub const SHM_STATUS_UNINITIALIZED: &str = "UNINITIALIZED";
pub const SHM_STATUS_ERROR: &str = "ERROR";
pub const SHM_STATUS_DISCONNECTED: &str = "DISCONNECTED";

pub fn resolve_arrow_signal_name(shm_name: &str, configured_name: Option<&str>) -> String {
    configured_name
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| format!("{shm_name}{L0_ARROW_SIGNAL_SUFFIX}"))
}

pub fn transport_constants() -> [(&'static str, &'static str); 10] {
    [
        ("L0_IPC_SIGNAL_ENV_KEY", L0_IPC_SIGNAL_ENV_KEY),
        ("L0_BATCH_INTERVAL_ENV_KEY", L0_BATCH_INTERVAL_ENV_KEY),
        ("L0_BATCH_MAX_ROWS_ENV_KEY", L0_BATCH_MAX_ROWS_ENV_KEY),
        ("L0_IPC_SHM_BYTES_ENV_KEY", L0_IPC_SHM_BYTES_ENV_KEY),
        ("L0_ARROW_SIGNAL_SUFFIX", L0_ARROW_SIGNAL_SUFFIX),
        ("SHM_STATUS_OK", SHM_STATUS_OK),
        ("SHM_STATUS_UNINITIALIZED", SHM_STATUS_UNINITIALIZED),
        ("SHM_STATUS_ERROR", SHM_STATUS_ERROR),
        ("SHM_STATUS_DISCONNECTED", SHM_STATUS_DISCONNECTED),
        ("_CONTRACT_VERSION", "1"),
    ]
}

#[pyfunction]
fn transport_contract_constants(py: Python<'_>) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    for (key, value) in transport_constants() {
        out.set_item(key, value)?;
    }
    out.set_item("DEFAULT_L0_BATCH_INTERVAL_MS", DEFAULT_L0_BATCH_INTERVAL_MS)?;
    out.set_item("DEFAULT_L0_BATCH_MAX_ROWS", DEFAULT_L0_BATCH_MAX_ROWS)?;
    out.set_item("DEFAULT_L0_IPC_SHM_BYTES", DEFAULT_L0_IPC_SHM_BYTES)?;
    out.set_item("DEFAULT_LONGPORT_CONNECT_RETRIES", DEFAULT_LONGPORT_CONNECT_RETRIES)?;
    out.set_item(
        "DEFAULT_LONGPORT_CONNECT_RETRY_BASE_SEC",
        DEFAULT_LONGPORT_CONNECT_RETRY_BASE_SEC,
    )?;
    out.set_item("DEFAULT_SHM_HEAD", DEFAULT_SHM_HEAD)?;
    out.set_item("DEFAULT_SHM_TAIL", DEFAULT_SHM_TAIL)?;
    Ok(out.unbind())
}

#[pyfunction]
#[pyo3(signature = (shm_name, configured_name=None))]
fn transport_resolve_arrow_signal_name(
    shm_name: &str,
    configured_name: Option<&str>,
) -> PyResult<String> {
    if shm_name.trim().is_empty() {
        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            "shared memory name is required",
        ));
    }
    Ok(resolve_arrow_signal_name(shm_name, configured_name))
}

#[pyfunction]
#[pyo3(signature = (status, head=None, tail=None))]
fn transport_build_shm_stats(
    py: Python<'_>,
    status: &str,
    head: Option<u64>,
    tail: Option<u64>,
) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("head", head.unwrap_or(DEFAULT_SHM_HEAD))?;
    out.set_item("tail", tail.unwrap_or(DEFAULT_SHM_TAIL))?;
    out.set_item("status", status)?;
    Ok(out.unbind())
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(transport_contract_constants, module)?)?;
    module.add_function(wrap_pyfunction!(transport_resolve_arrow_signal_name, module)?)?;
    module.add_function(wrap_pyfunction!(transport_build_shm_stats, module)?)?;
    Ok(())
}
