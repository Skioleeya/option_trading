use pyo3::prelude::*;
use pyo3::types::PyModule;

mod events;
mod governor;
mod observability;
mod quality;
mod sanitize;
mod store;
mod validators;

#[pymodule]
fn services_l0_support(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    events::register(py, m)?;
    governor::register(py, m)?;
    observability::register(py, m)?;
    quality::register(py, m)?;
    validators::register(py, m)?;
    sanitize::register(py, m)?;
    store::register(py, m)?;
    Ok(())
}
