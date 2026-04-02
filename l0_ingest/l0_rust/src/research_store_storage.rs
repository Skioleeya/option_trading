use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyModule};
use std::fs;
use std::path::Path;

fn pyarrow_modules<'py>(py: Python<'py>) -> PyResult<(Bound<'py, PyModule>, Bound<'py, PyModule>)> {
    let pa = py.import("pyarrow")?;
    let pq = py.import("pyarrow.parquet")?;
    Ok((pa, pq))
}

#[pyfunction]
fn service_research_records_to_parquet(py: Python<'_>, records: Bound<'_, PyAny>) -> PyResult<Vec<u8>> {
    let (pa, pq) = pyarrow_modules(py)?;
    let table_type = pa.getattr("Table")?;
    let table = table_type.call_method1("from_pylist", (records,))?;
    let sink = pa.getattr("BufferOutputStream")?.call0()?;
    let kwargs = PyDict::new(py);
    kwargs.set_item("compression", "zstd")?;
    kwargs.set_item("use_dictionary", true)?;
    pq.call_method(
        "write_table",
        (table, &sink),
        Some(&kwargs),
    )?;
    let buffer = sink.call_method0("getvalue")?;
    buffer.call_method0("to_pybytes")?.extract::<Vec<u8>>()
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
    let write_kwargs = PyDict::new(py);
    write_kwargs.set_item("compression", "zstd")?;
    write_kwargs.set_item("use_dictionary", true)?;
    pq.call_method(
        "write_table",
        (final_table, path),
        Some(&write_kwargs),
    )?;
    Ok(())
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
    module.add_function(wrap_pyfunction!(service_research_read_file_bytes, module)?)?;
    Ok(())
}
