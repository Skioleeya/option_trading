use pyo3::prelude::*;

mod l0_runtime_contracts;
mod metrics;
mod option_chain;
mod transport;

#[pymodule]
fn contracts(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    l0_runtime_contracts::register(py, m)?;
    transport::register(py, m)?;
    metrics::register(py, m)?;
    option_chain::register(py, m)?;
    Ok(())
}
