use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyModule};
use std::fs::{self, File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

fn pyarrow_modules<'py>(py: Python<'py>) -> PyResult<(Bound<'py, PyModule>, Bound<'py, PyModule>)> {
    let pa = py.import("pyarrow")?;
    let pq = py.import("pyarrow.parquet")?;
    Ok((pa, pq))
}

fn parquet_write_kwargs(py: Python<'_>) -> Bound<'_, PyDict> {
    let kwargs = PyDict::new(py);
    let _ = kwargs.set_item("compression", "zstd");
    let _ = kwargs.set_item("compression_level", 19);
    let _ = kwargs.set_item("use_dictionary", true);
    let _ = kwargs.set_item("write_statistics", false);
    kwargs
}

fn table_to_bytes(
    py: Python<'_>,
    pa: &Bound<'_, PyModule>,
    pq: &Bound<'_, PyModule>,
    table: &Bound<'_, PyAny>,
) -> PyResult<Vec<u8>> {
    let sink = pa.getattr("BufferOutputStream")?.call0()?;
    pq.call_method("write_table", (table, &sink), Some(&parquet_write_kwargs(py)))?;
    let buffer = sink.call_method0("getvalue")?;
    buffer.call_method0("to_pybytes")?.extract::<Vec<u8>>()
}

fn temp_path_for(target: &Path) -> PyResult<PathBuf> {
    let parent = target
        .parent()
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("parquet target has no parent directory"))?;
    let file_name = target
        .file_name()
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("parquet target has no file name"))?
        .to_string_lossy();
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|err| PyErr::new::<pyo3::exceptions::PyOSError, _>(err.to_string()))?
        .as_nanos();
    Ok(parent.join(format!(".{file_name}.tmp-{}-{nonce}", std::process::id())))
}

fn sync_parent_dir(parent: &Path) -> PyResult<()> {
    let dir = File::open(parent)
        .map_err(|err| PyErr::new::<pyo3::exceptions::PyOSError, _>(err.to_string()))?;
    dir.sync_all()
        .map_err(|err| PyErr::new::<pyo3::exceptions::PyOSError, _>(err.to_string()))
}

#[cfg(windows)]
fn replace_existing_file(temp_path: &Path, target_path: &Path) -> PyResult<()> {
    use std::iter;
    use std::os::windows::ffi::OsStrExt;
    use std::ptr;

    #[link(name = "Kernel32")]
    unsafe extern "system" {
        fn ReplaceFileW(
            lp_replaced_file_name: *const u16,
            lp_replacement_file_name: *const u16,
            lp_backup_file_name: *const u16,
            dw_replace_flags: u32,
            lp_exclude: *mut core::ffi::c_void,
            lp_reserved: *mut core::ffi::c_void,
        ) -> i32;
    }

    const REPLACEFILE_IGNORE_MERGE_ERRORS: u32 = 0x0000_0002;
    let target_wide: Vec<u16> = target_path
        .as_os_str()
        .encode_wide()
        .chain(iter::once(0))
        .collect();
    let temp_wide: Vec<u16> = temp_path
        .as_os_str()
        .encode_wide()
        .chain(iter::once(0))
        .collect();
    let ok = unsafe {
        ReplaceFileW(
            target_wide.as_ptr(),
            temp_wide.as_ptr(),
            ptr::null(),
            REPLACEFILE_IGNORE_MERGE_ERRORS,
            ptr::null_mut(),
            ptr::null_mut(),
        )
    };
    if ok == 0 {
        return Err(PyErr::new::<pyo3::exceptions::PyOSError, _>(
            std::io::Error::last_os_error().to_string(),
        ));
    }
    Ok(())
}

#[cfg(not(windows))]
fn replace_existing_file(temp_path: &Path, target_path: &Path) -> PyResult<()> {
    fs::rename(temp_path, target_path)
        .map_err(|err| PyErr::new::<pyo3::exceptions::PyOSError, _>(err.to_string()))?;
    let parent = target_path
        .parent()
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("parquet target has no parent directory"))?;
    sync_parent_dir(parent)
}

fn atomic_write_bytes(path: &Path, payload: &[u8]) -> PyResult<()> {
    let parent = path
        .parent()
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("parquet target has no parent directory"))?;
    fs::create_dir_all(parent)
        .map_err(|err| PyErr::new::<pyo3::exceptions::PyOSError, _>(err.to_string()))?;
    let temp_path = temp_path_for(path)?;
    let result = (|| -> PyResult<()> {
        {
            let mut file = OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&temp_path)
                .map_err(|err| PyErr::new::<pyo3::exceptions::PyOSError, _>(err.to_string()))?;
            file.write_all(payload)
                .map_err(|err| PyErr::new::<pyo3::exceptions::PyOSError, _>(err.to_string()))?;
            file.sync_all()
                .map_err(|err| PyErr::new::<pyo3::exceptions::PyOSError, _>(err.to_string()))?;
        }
        if path.exists() {
            replace_existing_file(&temp_path, path)?;
            Ok(())
        } else {
            fs::rename(&temp_path, path)
                .map_err(|err| PyErr::new::<pyo3::exceptions::PyOSError, _>(err.to_string()))?;
            #[cfg(not(windows))]
            {
                sync_parent_dir(parent)?;
            }
            Ok(())
        }
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temp_path);
    }
    result
}

#[pyfunction]
fn service_research_records_to_parquet(py: Python<'_>, records: Bound<'_, PyAny>) -> PyResult<Vec<u8>> {
    let (pa, pq) = pyarrow_modules(py)?;
    let table_type = pa.getattr("Table")?;
    let table = table_type.call_method1("from_pylist", (records,))?;
    table_to_bytes(py, &pa, &pq, &table)
}

#[pyfunction]
fn service_research_read_parquet_rows(py: Python<'_>, path: String) -> PyResult<Py<PyAny>> {
    let (_, pq) = pyarrow_modules(py)?;
    let table = pq.call_method1("read_table", (path,))?;
    Ok(table.call_method0("to_pylist")?.unbind().into())
}

#[pyfunction]
fn service_research_append_parquet_rows(
    py: Python<'_>,
    path: String,
    rows: Bound<'_, PyAny>,
    schema: Py<PyAny>,
) -> PyResult<()> {
    let (pa, pq) = pyarrow_modules(py)?;
    let table_type = pa.getattr("Table")?;
    let kwargs = PyDict::new(py);
    kwargs.set_item("schema", schema.bind(py))?;
    let table_new = table_type.call_method("from_pylist", (rows,), Some(&kwargs))?;
    let final_table = if Path::new(&path).exists() {
        let read_kwargs = PyDict::new(py);
        read_kwargs.set_item("schema", schema.bind(py))?;
        let table_old = pq.call_method("read_table", (path.as_str(),), Some(&read_kwargs))?;
        let tables = PyList::empty(py);
        tables.append(table_old)?;
        tables.append(&table_new)?;
        let concat_kwargs = PyDict::new(py);
        concat_kwargs.set_item("promote_options", "none")?;
        pa.call_method(
            "concat_tables",
            (tables,),
            Some(&concat_kwargs),
        )?
    } else {
        table_new
    };
    let bytes = table_to_bytes(py, &pa, &pq, &final_table)?;
    atomic_write_bytes(Path::new(&path), &bytes)
}

#[pyfunction]
fn service_research_write_parquet_rows(
    py: Python<'_>,
    path: String,
    rows: Bound<'_, PyAny>,
    schema: Py<PyAny>,
) -> PyResult<()> {
    let (pa, pq) = pyarrow_modules(py)?;
    let kwargs = PyDict::new(py);
    kwargs.set_item("schema", schema.bind(py))?;
    let table = pa
        .getattr("Table")?
        .call_method("from_pylist", (rows,), Some(&kwargs))?;
    let bytes = table_to_bytes(py, &pa, &pq, &table)?;
    atomic_write_bytes(Path::new(&path), &bytes)
}

#[pyfunction]
fn service_research_read_file_bytes(path: String) -> PyResult<Option<Vec<u8>>> {
    match fs::read(path) {
        Ok(bytes) => Ok(Some(bytes)),
        Err(err) if err.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(err) => Err(PyErr::new::<pyo3::exceptions::PyOSError, _>(err.to_string())),
    }
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(service_research_records_to_parquet, module)?)?;
    module.add_function(wrap_pyfunction!(service_research_read_parquet_rows, module)?)?;
    module.add_function(wrap_pyfunction!(service_research_append_parquet_rows, module)?)?;
    module.add_function(wrap_pyfunction!(service_research_write_parquet_rows, module)?)?;
    module.add_function(wrap_pyfunction!(service_research_read_file_bytes, module)?)?;
    Ok(())
}
