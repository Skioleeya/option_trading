use pyo3::prelude::*;
use pyo3::types::PyModule;

mod header_context;
mod history;
mod realized;
mod research_schema;
mod research_store_io;
mod research_pending_labels;
mod research_store_build;
mod research_store;
mod research_store_query;
mod research_store_support;
mod research_utils;
mod active_options;
mod tactical;
mod bsm;
mod aggregation;
mod aggregation_rust_bridge;
mod microstructure;
mod sabr;
mod fusion;
mod mm_flow;
mod mm_flow_snapshot;
mod atm_decay;

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
    bsm::register(py, m)?;
    aggregation::register(py, m)?;
    microstructure::register(py, m)?;
    sabr::register(py, m)?;
    fusion::register(py, m)?;
    mm_flow::register(m)?;
    atm_decay::register(m)?;
    Ok(())
}
