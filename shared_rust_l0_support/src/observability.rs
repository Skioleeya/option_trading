use pyo3::prelude::*;
use pyo3::types::{PyAny, PyModule};

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct NoOpCounter;
#[pymethods]
impl NoOpCounter {
    #[new] fn new() -> Self { Self }
    #[pyo3(signature = (_amount=1.0))]
    fn inc(&self, _amount: f64) {}
    fn labels(&self) -> Self { Self }
}

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct NoOpHistogram;
#[pymethods]
impl NoOpHistogram {
    #[new] fn new() -> Self { Self }
    fn observe(&self, _amount: f64) {}
    fn labels(&self) -> Self { Self }
    fn time(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let contextlib = py.import("contextlib")?;
        Ok(contextlib.getattr("nullcontext")?.call0()?.unbind().into_any())
    }
}

#[pyclass(frozen, module = "shared_rust.services_l0_support")]
pub struct L0Instrumentation;
#[pymethods]
impl L0Instrumentation {
    #[classattr]
    fn ingest_events_total(py: Python<'_>) -> PyResult<Py<NoOpCounter>> { Py::new(py, NoOpCounter) }
    #[classattr]
    fn sanitize_pass_total(py: Python<'_>) -> PyResult<Py<NoOpCounter>> { Py::new(py, NoOpCounter) }
    #[classattr]
    fn sanitize_drop_total(py: Python<'_>) -> PyResult<Py<NoOpCounter>> { Py::new(py, NoOpCounter) }
    #[classattr]
    fn breaker_trip_total(py: Python<'_>) -> PyResult<Py<NoOpCounter>> { Py::new(py, NoOpCounter) }
    #[classattr]
    fn store_commit_total(py: Python<'_>) -> PyResult<Py<NoOpCounter>> { Py::new(py, NoOpCounter) }
    #[classattr]
    fn ingest_latency_ms(py: Python<'_>) -> PyResult<Py<NoOpHistogram>> { Py::new(py, NoOpHistogram) }
    #[classattr]
    fn sanitize_latency_ms(py: Python<'_>) -> PyResult<Py<NoOpHistogram>> { Py::new(py, NoOpHistogram) }
}

#[pyfunction]
fn trace_ingest(func: Py<PyAny>) -> Py<PyAny> { func }
#[pyfunction]
fn trace_sanitize(func: Py<PyAny>) -> Py<PyAny> { func }
#[pyfunction]
fn trace_store(func: Py<PyAny>) -> Py<PyAny> { func }

pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<NoOpCounter>()?;
    m.add_class::<NoOpHistogram>()?;
    m.add_class::<L0Instrumentation>()?;
    m.add_function(wrap_pyfunction!(trace_ingest, m)?)?;
    m.add_function(wrap_pyfunction!(trace_sanitize, m)?)?;
    m.add_function(wrap_pyfunction!(trace_store, m)?)?;
    Ok(())
}
