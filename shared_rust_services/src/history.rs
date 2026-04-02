use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PySequence};
use std::collections::{HashMap, HashSet};

const COLUMNAR_SCHEMA_VERSION: &str = "v2";
const COLUMNAR_ENCODING: &str = "columnar-json";

fn row_as_pairs<'py>(row: &Bound<'py, PyAny>) -> PyResult<Vec<(String, Py<PyAny>)>> {
    let dict = row.downcast::<PyDict>().map_err(|_| {
        PyTypeError::new_err("history row must be a dict-like mapping")
    })?;
    let mut pairs = Vec::with_capacity(dict.len());
    for (key, value) in dict.iter() {
        let name = key.extract::<String>()?;
        pairs.push((name, value.unbind()));
    }
    Ok(pairs)
}

#[pyfunction]
fn history_columnar_schema_version() -> &'static str {
    COLUMNAR_SCHEMA_VERSION
}

#[pyfunction]
fn history_columnar_encoding() -> &'static str {
    COLUMNAR_ENCODING
}

#[pyfunction]
fn pack_rows_columnar(py: Python<'_>, rows: &Bound<'_, PyAny>) -> PyResult<(Vec<String>, Vec<Vec<Py<PyAny>>>)> {
    let items = rows.downcast::<PyList>().map_err(|_| PyTypeError::new_err("rows must be a list"))?;
    let mut seen = HashSet::new();
    let mut columns: Vec<String> = Vec::new();
    let mut parsed_rows: Vec<Vec<(String, Py<PyAny>)>> = Vec::with_capacity(items.len());

    for row in items.iter() {
        let pairs = row_as_pairs(&row)?;
        for (key, _) in &pairs {
            if seen.insert(key.clone()) {
                columns.push(key.clone());
            }
        }
        parsed_rows.push(pairs);
    }

    let mut matrix = Vec::with_capacity(parsed_rows.len());
    for row in parsed_rows {
        let dict: HashMap<String, Py<PyAny>> = row.into_iter().collect();
        let mut out_row = Vec::with_capacity(columns.len());
        for key in &columns {
            match dict.get(key) {
                Some(value) => out_row.push(value.clone_ref(py)),
                None => out_row.push(py.None()),
            }
        }
        matrix.push(out_row);
    }

    Ok((columns, matrix))
}

#[pyfunction]
#[pyo3(signature = (rows, count=None, meta=None))]
fn build_columnar_payload(
    py: Python<'_>,
    rows: &Bound<'_, PyAny>,
    count: Option<usize>,
    meta: Option<&Bound<'_, PyAny>>,
) -> PyResult<Py<PyDict>> {
    let (columns, matrix) = pack_rows_columnar(py, rows)?;
    let payload = PyDict::new(py);
    payload.set_item("schema", COLUMNAR_SCHEMA_VERSION)?;
    payload.set_item("encoding", COLUMNAR_ENCODING)?;
    payload.set_item("columns", columns)?;
    payload.set_item("rows", matrix)?;
    let row_count = rows.downcast::<PySequence>()?.len().unwrap_or(0) as usize;
    payload.set_item("count", count.unwrap_or(row_count))?;
    if let Some(meta_any) = meta {
        let meta_dict = meta_any.downcast::<PyDict>().map_err(|_| {
            PyTypeError::new_err("meta must be a mapping")
        })?;
        for (key, value) in meta_dict.iter() {
            payload.set_item(key, value)?;
        }
    }
    Ok(payload.unbind())
}

pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(history_columnar_schema_version, m)?)?;
    m.add_function(wrap_pyfunction!(history_columnar_encoding, m)?)?;
    m.add_function(wrap_pyfunction!(pack_rows_columnar, m)?)?;
    m.add_function(wrap_pyfunction!(build_columnar_payload, m)?)?;
    Ok(())
}
