use pyo3::prelude::*;

mod agent;
mod enums;
mod flow;
mod helpers;
mod micro_core;
mod micro_state;

#[pymodule]
fn models(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    enums::register(m)?;
    flow::register(py, m)?;
    micro_core::register(py, m)?;
    micro_state::register(py, m)?;
    agent::register(py, m)?;
    Ok(())
}
