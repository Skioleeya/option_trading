use pyo3::exceptions::PyRuntimeError;
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

fn get_env_value(env: Option<&Bound<'_, PyDict>>, key: &str) -> PyResult<Option<String>> {
    match env {
        None => Ok(None),
        Some(mapping) => match mapping.get_item(key)? {
            None => Ok(None),
            Some(value) => Ok(Some(value.extract::<String>()?)),
        },
    }
}

fn resolve_arrow_signal_name_inner(shm_name: &str, configured_name: Option<&str>) -> String {
    configured_name
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(ToOwned::to_owned)
        .unwrap_or_else(|| format!("{shm_name}{L0_ARROW_SIGNAL_SUFFIX}"))
}

#[pyfunction]
#[pyo3(signature = (shm_name, *, env=None))]
fn resolve_arrow_signal_name(shm_name: &str, env: Option<&Bound<'_, PyDict>>) -> PyResult<String> {
    if shm_name.trim().is_empty() {
        return Err(PyRuntimeError::new_err("shared memory name is required"));
    }
    let configured_name = get_env_value(env, L0_IPC_SIGNAL_ENV_KEY)?;
    Ok(resolve_arrow_signal_name_inner(
        shm_name,
        configured_name.as_deref(),
    ))
}

#[pyfunction]
#[pyo3(signature = (status, *, head=DEFAULT_SHM_HEAD, tail=DEFAULT_SHM_TAIL))]
fn build_shm_stats(
    py: Python<'_>,
    status: &str,
    head: u64,
    tail: u64,
) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("head", head)?;
    out.set_item("tail", tail)?;
    out.set_item("status", status)?;
    Ok(out.unbind())
}

fn add_str(module: &Bound<'_, PyModule>, name: &str, value: &str) -> PyResult<()> {
    module.add(name, value)
}

fn add_u64(module: &Bound<'_, PyModule>, name: &str, value: u64) -> PyResult<()> {
    module.add(name, value)
}

fn add_usize(module: &Bound<'_, PyModule>, name: &str, value: usize) -> PyResult<()> {
    module.add(name, value)
}

pub fn register(py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    let _ = py;
    add_str(module, "L0_IPC_SIGNAL_ENV_KEY", L0_IPC_SIGNAL_ENV_KEY)?;
    add_str(module, "L0_BATCH_INTERVAL_ENV_KEY", L0_BATCH_INTERVAL_ENV_KEY)?;
    add_str(module, "L0_BATCH_MAX_ROWS_ENV_KEY", L0_BATCH_MAX_ROWS_ENV_KEY)?;
    add_str(module, "L0_IPC_SHM_BYTES_ENV_KEY", L0_IPC_SHM_BYTES_ENV_KEY)?;
    add_str(module, "L0_ARROW_SIGNAL_SUFFIX", L0_ARROW_SIGNAL_SUFFIX)?;
    add_u64(module, "DEFAULT_L0_BATCH_INTERVAL_MS", DEFAULT_L0_BATCH_INTERVAL_MS)?;
    add_usize(module, "DEFAULT_L0_BATCH_MAX_ROWS", DEFAULT_L0_BATCH_MAX_ROWS)?;
    add_usize(module, "DEFAULT_L0_IPC_SHM_BYTES", DEFAULT_L0_IPC_SHM_BYTES)?;
    add_u64(
        module,
        "DEFAULT_LONGPORT_CONNECT_RETRIES",
        DEFAULT_LONGPORT_CONNECT_RETRIES,
    )?;
    module.add(
        "DEFAULT_LONGPORT_CONNECT_RETRY_BASE_SEC",
        DEFAULT_LONGPORT_CONNECT_RETRY_BASE_SEC,
    )?;
    add_u64(module, "DEFAULT_SHM_HEAD", DEFAULT_SHM_HEAD)?;
    add_u64(module, "DEFAULT_SHM_TAIL", DEFAULT_SHM_TAIL)?;
    add_str(module, "SHM_STATUS_OK", SHM_STATUS_OK)?;
    add_str(module, "SHM_STATUS_UNINITIALIZED", SHM_STATUS_UNINITIALIZED)?;
    add_str(module, "SHM_STATUS_ERROR", SHM_STATUS_ERROR)?;
    add_str(module, "SHM_STATUS_DISCONNECTED", SHM_STATUS_DISCONNECTED)?;
    module.add_function(wrap_pyfunction!(resolve_arrow_signal_name, module)?)?;
    module.add_function(wrap_pyfunction!(build_shm_stats, module)?)?;
    Ok(())
}
