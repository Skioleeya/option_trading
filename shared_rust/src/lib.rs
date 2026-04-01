use pyo3::prelude::*;

mod metrics;
mod option_chain;
mod transport;

#[pymodule]
fn contracts(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    transport::register(py, m)?;
    metrics::register(py, m)?;
    option_chain::register(py, m)?;
    Ok(())
}
