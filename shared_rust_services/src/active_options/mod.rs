use pyo3::prelude::*;
use pyo3::types::PyModule;

mod common;
mod diagnostics;
mod engines;
mod fallback;
mod input;
mod support;

pub fn register(py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    engines::register(py, module)?;
    input::register(py, module)?;
    support::register(py, module)?;
    fallback::register(py, module)?;
    diagnostics::register(py, module)?;
    Ok(())
}
