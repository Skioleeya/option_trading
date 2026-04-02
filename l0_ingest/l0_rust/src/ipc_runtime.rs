use crate::ipc_legacy::{ArrowIpcSegment, DEFAULT_ARROW_IPC_BYTES};
use crate::windows_signal::WindowsSignal;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::PyModule;

#[pyclass]
pub struct NativeSignalListener {
    signal: Option<WindowsSignal>,
}

#[pymethods]
impl NativeSignalListener {
    #[new]
    fn new(signal_name: &str) -> PyResult<Self> {
        if signal_name.trim().is_empty() {
            return Err(PyRuntimeError::new_err("signal name is required"));
        }
        let signal = WindowsSignal::connect(signal_name).map_err(PyRuntimeError::new_err)?;
        Ok(Self {
            signal: Some(signal),
        })
    }

    fn wait(&self, py: Python<'_>) -> PyResult<()> {
        let signal = self
            .signal
            .as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("signal listener is not connected"))?;
        py.allow_threads(|| signal.wait().map_err(PyRuntimeError::new_err))
    }

    fn close(&mut self) {
        self.signal = None;
    }
}

#[pyclass]
pub struct NativeArrowIpcReader {
    segment: Option<ArrowIpcSegment>,
    signal: Option<WindowsSignal>,
}

#[pymethods]
impl NativeArrowIpcReader {
    #[new]
    #[pyo3(signature = (shm_name, signal_name, capacity_bytes=DEFAULT_ARROW_IPC_BYTES))]
    fn new(shm_name: &str, signal_name: &str, capacity_bytes: usize) -> PyResult<Self> {
        if shm_name.trim().is_empty() {
            return Err(PyRuntimeError::new_err("shared memory name is required"));
        }
        if signal_name.trim().is_empty() {
            return Err(PyRuntimeError::new_err("signal name is required"));
        }
        let normalized_capacity = capacity_bytes.max(1);
        let segment = ArrowIpcSegment::open_readonly(shm_name, normalized_capacity)
            .map_err(PyRuntimeError::new_err)?;
        let signal = WindowsSignal::connect(signal_name).map_err(PyRuntimeError::new_err)?;
        Ok(Self {
            segment: Some(segment),
            signal: Some(signal),
        })
    }

    fn read_next_payload(&self, py: Python<'_>) -> PyResult<Vec<u8>> {
        let signal = self
            .signal
            .as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("signal listener is not connected"))?;
        let segment = self
            .segment
            .as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("ArrowIpcReader is not connected"))?;
        py.allow_threads(|| signal.wait().map_err(PyRuntimeError::new_err))?;
        segment.read_message().map_err(PyRuntimeError::new_err)
    }

    fn close(&mut self) {
        self.signal = None;
        self.segment = None;
    }
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<NativeSignalListener>()?;
    module.add_class::<NativeArrowIpcReader>()?;
    Ok(())
}
