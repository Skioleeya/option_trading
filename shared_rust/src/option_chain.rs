use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyModule};

#[derive(Clone, Copy)]
struct FieldSpec {
    name: &'static str,
    type_name: &'static str,
}

const FIELD_SPECS: [FieldSpec; 11] = [
    FieldSpec { name: "symbol", type_name: "string" },
    FieldSpec { name: "strike", type_name: "float64" },
    FieldSpec { name: "is_call", type_name: "bool_" },
    FieldSpec { name: "bid", type_name: "float64" },
    FieldSpec { name: "ask", type_name: "float64" },
    FieldSpec { name: "iv", type_name: "float64" },
    FieldSpec { name: "volume", type_name: "float64" },
    FieldSpec { name: "current_volume", type_name: "float64" },
    FieldSpec { name: "turnover", type_name: "float64" },
    FieldSpec { name: "open_interest", type_name: "float64" },
    FieldSpec { name: "contract_multiplier", type_name: "float64" },
];

fn mapping_item<'py>(row: &Bound<'py, PyAny>, key: &str) -> PyResult<Option<Bound<'py, PyAny>>> {
    let value = row.call_method1("get", (key,))?;
    if value.is_none() {
        return Ok(None);
    }
    Ok(Some(value))
}

fn string_or_default(row: &Bound<'_, PyAny>, key: &str, default: &str) -> PyResult<String> {
    Ok(mapping_item(row, key)?
        .and_then(|value| value.extract::<String>().ok())
        .unwrap_or_else(|| default.to_string()))
}

fn f64_or_default(row: &Bound<'_, PyAny>, key: &str, default: f64) -> PyResult<f64> {
    Ok(mapping_item(row, key)?
        .and_then(|value| value.extract::<f64>().ok())
        .unwrap_or(default))
}

fn pyarrow_type(pyarrow: &Bound<'_, PyModule>, type_name: &str) -> PyResult<Py<PyAny>> {
    let func = pyarrow.getattr(type_name)?;
    Ok(func.call0()?.unbind())
}

fn build_schema(py: Python<'_>) -> PyResult<Py<PyAny>> {
    let pyarrow = py.import("pyarrow")?;
    let fields = PyList::empty(py);
    for field in FIELD_SPECS {
        let field_fn = pyarrow.getattr("field")?;
        let ty = pyarrow_type(&pyarrow, field.type_name)?;
        fields.append(field_fn.call1((field.name, ty))?)?;
    }
    Ok(pyarrow.getattr("schema")?.call1((fields,))?.unbind())
}

fn build_arrays_dict<'py>(
    py: Python<'py>,
    chain_snapshot: Bound<'py, PyAny>,
) -> PyResult<Bound<'py, PyDict>> {
    let out = PyDict::new(py);
    for key in [
        "symbol",
        "strike",
        "is_call",
        "bid",
        "ask",
        "iv",
        "volume",
        "current_volume",
        "turnover",
        "open_interest",
        "contract_multiplier",
    ] {
        out.set_item(key, PyList::empty(py))?;
    }
    for item in chain_snapshot.try_iter()? {
        let row = item?;
        out.get_item("symbol")?.expect("symbol").downcast_into::<PyList>()?.append(string_or_default(&row, "symbol", "")?)?;
        out.get_item("strike")?.expect("strike").downcast_into::<PyList>()?.append(f64_or_default(&row, "strike", 0.0)?)?;
        let option_type = string_or_default(&row, "type", "CALL")?;
        let is_call = matches!(option_type.to_ascii_uppercase().as_str(), "CALL" | "C");
        out.get_item("is_call")?.expect("is_call").downcast_into::<PyList>()?.append(is_call)?;
        out.get_item("bid")?.expect("bid").downcast_into::<PyList>()?.append(f64_or_default(&row, "bid", 0.0)?)?;
        out.get_item("ask")?.expect("ask").downcast_into::<PyList>()?.append(f64_or_default(&row, "ask", 0.0)?)?;
        let iv = mapping_item(&row, "iv")?
            .and_then(|value| value.extract::<f64>().ok())
            .or_else(|| mapping_item(&row, "implied_volatility").ok().flatten().and_then(|value| value.extract::<f64>().ok()))
            .unwrap_or(0.0);
        out.get_item("iv")?.expect("iv").downcast_into::<PyList>()?.append(iv)?;
        out.get_item("volume")?.expect("volume").downcast_into::<PyList>()?.append(f64_or_default(&row, "volume", 0.0)?)?;
        out.get_item("current_volume")?.expect("current_volume").downcast_into::<PyList>()?.append(f64_or_default(&row, "current_volume", 0.0)?)?;
        out.get_item("turnover")?.expect("turnover").downcast_into::<PyList>()?.append(f64_or_default(&row, "turnover", 0.0)?)?;
        out.get_item("open_interest")?.expect("open_interest").downcast_into::<PyList>()?.append(f64_or_default(&row, "open_interest", 0.0)?)?;
        out.get_item("contract_multiplier")?.expect("contract_multiplier").downcast_into::<PyList>()?.append(f64_or_default(&row, "contract_multiplier", 100.0)?)?;
    }
    Ok(out)
}

#[pyfunction]
fn dicts_to_record_batch(py: Python<'_>, chain_snapshot: Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    let pyarrow = py.import("pyarrow")?;
    let arrays = build_arrays_dict(py, chain_snapshot)?;
    let kwargs = PyDict::new(py);
    kwargs.set_item("schema", build_schema(py)?)?;
    Ok(pyarrow
        .getattr("RecordBatch")?
        .getattr("from_pydict")?
        .call((arrays,), Some(&kwargs))?
        .unbind())
}

#[pyfunction]
fn ensure_record_batch(py: Python<'_>, data: Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    let builtins = py.import("builtins")?;
    let pyarrow = py.import("pyarrow")?;
    let is_record_batch = builtins
        .getattr("isinstance")?
        .call1((&data, pyarrow.getattr("RecordBatch")?))?
        .extract::<bool>()?;
    if is_record_batch {
        return Ok(data.unbind());
    }
    dicts_to_record_batch(py, data)
}

pub fn register(py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add("OPTION_CHAIN_SCHEMA", build_schema(py)?)?;
    module.add_function(wrap_pyfunction!(dicts_to_record_batch, module)?)?;
    module.add_function(wrap_pyfunction!(ensure_record_batch, module)?)?;
    Ok(())
}
