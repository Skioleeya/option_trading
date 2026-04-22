use pyo3::exceptions::{PyAttributeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyTuple};
use pyo3::PyClass;
use std::collections::BTreeMap;

pub type FieldMap = BTreeMap<String, Py<PyAny>>;

pub fn kwargs_to_fields(py: Python<'_>, kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<FieldMap> {
    let mut fields = FieldMap::new();
    if let Some(kwargs) = kwargs {
        for (key, value) in kwargs.iter() {
            fields.insert(key.extract::<String>()?, value.unbind());
        }
    }
    Ok(fields)
}

pub fn get_attr(py: Python<'_>, fields: &FieldMap, name: &str) -> PyResult<Py<PyAny>> {
    fields
        .get(name)
        .map(|value| value.clone_ref(py))
        .ok_or_else(|| PyAttributeError::new_err(format!("unknown field: {name}")))
}

pub fn set_attr(fields: &mut FieldMap, name: &str, value: Py<PyAny>) {
    fields.insert(name.to_string(), value);
}

pub fn merge_fields(target: &mut FieldMap, source: FieldMap) {
    for (key, value) in source {
        target.insert(key, value);
    }
}

pub fn clone_fields(py: Python<'_>, fields: &FieldMap) -> FieldMap {
    let mut out = FieldMap::new();
    for (key, value) in fields {
        out.insert(key.clone(), value.clone_ref(py));
    }
    out
}

pub fn model_dump_fields(py: Python<'_>, fields: &FieldMap) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    for (key, value) in fields {
        out.set_item(key, dump_value(py, value.bind(py))?)?;
    }
    Ok(out.unbind())
}

pub fn dump_value(py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    if value.hasattr("model_dump")? {
        return Ok(value.call_method0("model_dump")?.unbind());
    }
    if let Ok(mapping) = value.downcast::<PyDict>() {
        let out = PyDict::new(py);
        for (key, inner) in mapping.iter() {
            out.set_item(key, dump_value(py, &inner)?)?;
        }
        return Ok(out.unbind().into_any());
    }
    if let Ok(items) = value.downcast::<PyList>() {
        let out = PyList::empty(py);
        for inner in items.iter() {
            out.append(dump_value(py, &inner)?)?;
        }
        return Ok(out.unbind().into_any());
    }
    if let Ok(items) = value.downcast::<PyTuple>() {
        let out = PyList::empty(py);
        for inner in items.iter() {
            out.append(dump_value(py, &inner)?)?;
        }
        return Ok(out.unbind().into_any());
    }
    Ok(value.clone().unbind())
}

pub fn clone_or_from_kwargs<T>(
    data: &Bound<'_, PyAny>,
    build: impl Fn(Python<'_>, Option<&Bound<'_, PyDict>>) -> PyResult<T>,
) -> PyResult<T>
where
    T: PyClass,
{
    if let Ok(mapping) = data.downcast::<PyDict>() {
        return build(data.py(), Some(&mapping));
    }
    if data.hasattr("model_dump")? {
        let dumped = data.call_method0("model_dump")?;
        let mapping = dumped.downcast::<PyDict>()?;
        return build(data.py(), Some(&mapping));
    }
    Err(PyValueError::new_err("model_validate expects dict or model_dump-capable instance"))
}

pub fn finite_f64(fields: &FieldMap, name: &str, py: Python<'_>) -> PyResult<()> {
    if let Some(value) = fields.get(name) {
        let parsed = value.bind(py).extract::<f64>()?;
        if !parsed.is_finite() {
            return Err(PyValueError::new_err(format!("{name} must be finite")));
        }
    }
    Ok(())
}

pub fn py_none(py: Python<'_>) -> Py<PyAny> {
    py.None()
}

pub fn py_bool(py: Python<'_>, value: bool) -> PyResult<Py<PyAny>> {
    Ok(value.into_pyobject(py)?.to_owned().unbind().into_any())
}

pub fn py_i64(py: Python<'_>, value: i64) -> PyResult<Py<PyAny>> {
    Ok(value.into_pyobject(py)?.to_owned().unbind().into_any())
}

pub fn py_f64(py: Python<'_>, value: f64) -> PyResult<Py<PyAny>> {
    Ok(value.into_pyobject(py)?.to_owned().unbind().into_any())
}

pub fn py_str(py: Python<'_>, value: &str) -> PyResult<Py<PyAny>> {
    Ok(value.into_pyobject(py)?.to_owned().unbind().into_any())
}

pub fn py_dict(py: Python<'_>) -> Py<PyAny> {
    PyDict::new(py).unbind().into_any()
}

pub fn py_list(py: Python<'_>) -> Py<PyAny> {
    PyList::empty(py).unbind().into_any()
}
