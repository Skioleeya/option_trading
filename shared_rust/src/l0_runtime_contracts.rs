use pyo3::prelude::*;
use pyo3::types::PyModule;

#[pyclass]
#[derive(Default)]
pub struct CallbackHooks {
    #[pyo3(get, set)]
    pub on_depth: Option<PyObject>,
    #[pyo3(get, set)]
    pub on_trade: Option<PyObject>,
}

#[pymethods]
impl CallbackHooks {
    #[new]
    fn new() -> Self {
        Self::default()
    }
}

#[pyclass(frozen)]
#[derive(Clone, Copy)]
pub struct SnapshotRequest {
    #[pyo3(get)]
    pub include_chain_arrow: bool,
}

#[pymethods]
impl SnapshotRequest {
    #[new]
    #[pyo3(signature = (include_chain_arrow = false))]
    fn new(include_chain_arrow: bool) -> Self {
        Self { include_chain_arrow }
    }
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<CallbackHooks>()?;
    module.add_class::<SnapshotRequest>()?;
    Ok(())
}
