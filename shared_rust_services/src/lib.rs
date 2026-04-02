use pyo3::prelude::*;
use pyo3::types::PyModule;

mod header_context;
mod history;
mod realized;
mod research_schema;
mod research_store;
mod research_store_support;
mod research_utils;
mod active_options;
mod tactical;

#[pymodule]
fn services(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    history::register(py, m)?;
    header_context::register(py, m)?;
    realized::register(py, m)?;
    active_options::register(py, m)?;
    research_utils::register(py, m)?;
    research_schema::register(py, m)?;
    research_store::register(py, m)?;
    tactical::register(py, m)?;
    Ok(())
}
