use crate::arrow_ipc::{ArrowIpcReadCursor, ArrowIpcSegment, DEFAULT_ARROW_IPC_BYTES};
use crate::windows_signal::WindowsSignal;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3::types::PyModule;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

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
    segment: Arc<ArrowIpcSegment>,
    signal: Arc<WindowsSignal>,
    cursor: Mutex<ArrowIpcReadCursor>,
    closed: AtomicBool,
}

impl NativeArrowIpcReader {
    fn connect(shm_name: &str, signal_name: &str, capacity_bytes: usize) -> PyResult<Self> {
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
            segment: Arc::new(segment),
            signal: Arc::new(signal),
            cursor: Mutex::new(ArrowIpcReadCursor::default()),
            closed: AtomicBool::new(false),
        })
    }

    fn read_next_payload_blocking(&self) -> PyResult<Vec<u8>> {
        if self.closed.load(Ordering::Acquire) {
            return Err(PyRuntimeError::new_err("ArrowIpcReader is closed"));
        }
        loop {
            self.signal.wait().map_err(PyRuntimeError::new_err)?;
            if self.closed.load(Ordering::Acquire) {
                return Err(PyRuntimeError::new_err("ArrowIpcReader is closed"));
            }
            let mut cursor = self
                .cursor
                .lock()
                .map_err(|_| PyRuntimeError::new_err("ArrowIpcReader cursor lock poisoned"))?;
            if let Some(payload) = self
                .segment
                .read_next_message(&mut cursor)
                .map_err(PyRuntimeError::new_err)?
            {
                return Ok(payload);
            }
        }
    }

    fn request_close(&self) {
        if self.closed.swap(true, Ordering::AcqRel) {
            return;
        }
        let _ = self.signal.signal();
        if let Ok(mut cursor) = self.cursor.lock() {
            *cursor = ArrowIpcReadCursor::default();
        }
    }

    fn diagnostics_snapshot(&self) -> PyResult<(u64, u64, u64, u64, u64)> {
        let cursor = self
            .cursor
            .lock()
            .map_err(|_| PyRuntimeError::new_err("ArrowIpcReader cursor lock poisoned"))?;
        let snapshot = self.segment.diagnostics(&cursor);
        Ok((
            snapshot.writer_batch_id,
            snapshot.reader_last_batch_id,
            snapshot.queued_batch_count,
            snapshot.dropped_batch_count,
            snapshot.reader_gap_count,
        ))
    }
}

#[pymethods]
impl NativeArrowIpcReader {
    #[new]
    #[pyo3(signature = (shm_name, signal_name, capacity_bytes=DEFAULT_ARROW_IPC_BYTES))]
    fn new(shm_name: &str, signal_name: &str, capacity_bytes: usize) -> PyResult<Self> {
        Self::connect(shm_name, signal_name, capacity_bytes)
    }

    fn read_next_payload(&self, py: Python<'_>) -> PyResult<Vec<u8>> {
        py.allow_threads(|| self.read_next_payload_blocking())
    }

    fn diagnostics(&self, py: Python<'_>) -> PyResult<PyObject> {
        let (writer_batch_id, reader_last_batch_id, queued_batch_count, dropped_batch_count, reader_gap_count) =
            self.diagnostics_snapshot()?;
        let out = PyDict::new(py);
        out.set_item("writer_batch_id", writer_batch_id)?;
        out.set_item("reader_last_batch_id", reader_last_batch_id)?;
        out.set_item("queued_batch_count", queued_batch_count)?;
        out.set_item("dropped_batch_count", dropped_batch_count)?;
        out.set_item("reader_gap_count", reader_gap_count)?;
        Ok(out.into_any().unbind())
    }

    fn close(&self) {
        self.request_close();
    }
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<NativeSignalListener>()?;
    module.add_class::<NativeArrowIpcReader>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::NativeArrowIpcReader;
    use crate::arrow_ipc::{ArrowIpcSegment, DEFAULT_ARROW_IPC_BYTES};
    use crate::windows_signal::WindowsSignal;
    use std::sync::Arc;
    use std::thread;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn unique_name(prefix: &str) -> String {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock before unix epoch")
            .as_nanos();
        format!("{prefix}_{nanos}")
    }

    #[test]
    fn native_arrow_ipc_reader_close_unblocks_waiter() {
        let shm_name = unique_name("arrow_ipc_reader_close_shm");
        let signal_name = unique_name("arrow_ipc_reader_close_signal");
        let _writer = ArrowIpcSegment::create_or_open(&shm_name, DEFAULT_ARROW_IPC_BYTES).expect("writer");
        let signal = WindowsSignal::create_or_open(&signal_name).expect("signal");
        let reader = Arc::new(
            NativeArrowIpcReader::connect(&shm_name, &signal_name, DEFAULT_ARROW_IPC_BYTES).expect("reader"),
        );

        let worker = {
            let reader = Arc::clone(&reader);
            thread::spawn(move || reader.read_next_payload_blocking())
        };

        signal.signal().expect("initial wake");
        reader.request_close();

        let result = worker.join().expect("worker thread");
        let message = result.expect_err("close should interrupt blocking read").to_string();
        assert!(message.contains("ArrowIpcReader is closed"), "unexpected message: {message}");
    }
}
