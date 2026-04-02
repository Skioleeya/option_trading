use super::common::{as_dict, as_list, logger, py_dict_get, py_to_f64, py_to_string, round_to};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyModule, PyType};

const EMPTY_CHAIN_REASON: &str = "empty_chain";
const INVALID_SPOT_REASON: &str = "invalid_spot";

#[pyclass(module = "shared_rust.services", unsendable)]
pub struct ActiveOptionsInputSnapshotData {
    #[pyo3(get)]
    chain: Py<PyList>,
    #[pyo3(get)]
    spot: f64,
    #[pyo3(get)]
    atm_iv: f64,
    #[pyo3(get)]
    ttm_seconds: Option<f64>,
    #[pyo3(get)]
    source_version: i64,
    #[pyo3(get)]
    source_timestamp_utc: Option<String>,
    #[pyo3(get)]
    valid: bool,
    #[pyo3(get)]
    invalid_reason: Option<String>,
}

#[pymethods]
impl ActiveOptionsInputSnapshotData {
    #[new]
    #[pyo3(signature = (*, chain, spot, atm_iv, ttm_seconds=None, source_version=0, source_timestamp_utc=None, valid=false, invalid_reason=None))]
    fn new(
        chain: Py<PyList>,
        spot: f64,
        atm_iv: f64,
        ttm_seconds: Option<f64>,
        source_version: i64,
        source_timestamp_utc: Option<String>,
        valid: bool,
        invalid_reason: Option<String>,
    ) -> Self {
        Self {
            chain,
            spot,
            atm_iv,
            ttm_seconds,
            source_version,
            source_timestamp_utc,
            valid,
            invalid_reason,
        }
    }

    #[classmethod]
    fn model_validate(_cls: &Bound<'_, PyType>, data: &Bound<'_, PyAny>) -> PyResult<Self> {
        let mapping = as_dict(data)?;
        Ok(Self {
            chain: mapping
                .get_item("chain")?
                .unwrap_or_else(|| PyList::empty(data.py()).into_any())
                .downcast::<PyList>()?
                .clone()
                .unbind(),
            spot: py_to_f64(mapping.get_item("spot")?.as_ref()),
            atm_iv: py_to_f64(mapping.get_item("atm_iv")?.as_ref()),
            ttm_seconds: mapping
                .get_item("ttm_seconds")?
                .and_then(|value| value.extract::<f64>().ok()),
            source_version: mapping
                .get_item("source_version")?
                .and_then(|value| value.extract::<i64>().ok())
                .unwrap_or(0),
            source_timestamp_utc: mapping
                .get_item("source_timestamp_utc")?
                .and_then(|value| value.extract::<String>().ok()),
            valid: mapping
                .get_item("valid")?
                .and_then(|value| value.extract::<bool>().ok())
                .unwrap_or(false),
            invalid_reason: mapping
                .get_item("invalid_reason")?
                .and_then(|value| value.extract::<String>().ok()),
        })
    }
}

fn clone_chain(py: Python<'_>, rows: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyList>> {
    let list = PyList::empty(py);
    if let Some(value) = rows {
        for row in as_list(value)?.iter() {
            if let Ok(dict) = row.downcast::<PyDict>() {
                list.append(dict.copy()?)?;
            }
        }
    }
    Ok(list.unbind())
}

fn option_type_of(row: &Bound<'_, PyDict>) -> String {
    let token = py_to_string(py_dict_get(row, "option_type").as_ref())
        .or_else(|| py_to_string(py_dict_get(row, "type").as_ref()))
        .unwrap_or_default()
        .trim()
        .to_uppercase();
    if matches!(token.as_str(), "CALL" | "C") {
        "CALL".to_string()
    } else if matches!(token.as_str(), "PUT" | "P") {
        "PUT".to_string()
    } else if py_to_f64(py_dict_get(row, "is_call").as_ref()) > 0.0 {
        "CALL".to_string()
    } else {
        "PUT".to_string()
    }
}

fn row_key(row: &Bound<'_, PyDict>, index: usize) -> String {
    if let Some(symbol) = py_to_string(py_dict_get(row, "symbol").as_ref()) {
        let normalized = symbol.trim().to_uppercase();
        if !normalized.is_empty() {
            return normalized;
        }
    }
    let strike = py_to_f64(py_dict_get(row, "strike").as_ref())
        .max(py_to_f64(py_dict_get(row, "strike_price").as_ref()));
    format!(
        "fallback:{index}:{}:{}",
        option_type_of(row),
        round_to(strike.max(0.0), 4)
    )
}

fn promote_fields(row: &Bound<'_, PyDict>) -> PyResult<()> {
    for (computed, aliases) in [
        ("computed_iv", vec!["implied_volatility", "iv"]),
        ("computed_gamma", vec!["gamma"]),
        ("computed_vanna", vec!["vanna"]),
        ("computed_delta", vec!["delta"]),
    ] {
        if let Some(value) = row.get_item(computed)? {
            if !value.is_none() {
                for alias in aliases {
                    row.set_item(alias, &value)?;
                }
            }
        }
    }
    Ok(())
}

fn source_timestamp_utc(l0_snapshot: &Bound<'_, PyDict>) -> PyResult<Option<String>> {
    let raw = l0_snapshot
        .get_item("as_of_utc")?
        .or_else(|| l0_snapshot.get_item("as_of").ok().flatten());
    let Some(value) = raw else {
        return Ok(None);
    };
    let text = value.str()?.to_str()?.trim().to_string();
    if text.is_empty() {
        return Ok(None);
    }
    Ok(Some(if text.ends_with('Z') {
        format!("{}+00:00", &text[..text.len() - 1])
    } else {
        text
    }))
}

#[pyfunction]
#[pyo3(signature = (*, l0_snapshot, l1_snapshot))]
fn build_active_options_input_snapshot(
    py: Python<'_>,
    l0_snapshot: &Bound<'_, PyAny>,
    l1_snapshot: &Bound<'_, PyAny>,
) -> PyResult<ActiveOptionsInputSnapshotData> {
    let l0_snapshot = as_dict(l0_snapshot)?;
    let l0_rows = clone_chain(py, l0_snapshot.get_item("chain")?.as_ref())?;
    let l1_chain = l1_snapshot
        .getattr("chain")
        .ok()
        .or_else(|| as_dict(l1_snapshot).ok().and_then(|mapping| mapping.get_item("chain").ok().flatten()));
    let l1_rows = clone_chain(py, l1_chain.as_ref())?;

    let merged = PyList::empty(py);
    let l1_by_key = PyDict::new(py);
    for (index, row) in l1_rows.bind(py).iter().enumerate() {
        let row = row.downcast::<PyDict>()?;
        l1_by_key.set_item(row_key(row, index), row.copy()?)?;
    }

    for (index, row) in l0_rows.bind(py).iter().enumerate() {
        let l0_row = row.downcast::<PyDict>()?;
        let key = row_key(l0_row, index);
        if let Some(other) = l1_by_key.get_item(&key)? {
            let merged_row = l0_row.copy()?;
            let other = other.downcast::<PyDict>()?;
            for (name, value) in other.iter() {
                if !value.is_none() {
                    merged_row.set_item(name, value)?;
                }
            }
            promote_fields(&merged_row)?;
            merged.append(merged_row)?;
            l1_by_key.del_item(&key)?;
        } else {
            merged.append(l0_row.copy()?)?;
        }
    }

    for (_, value) in l1_by_key.iter() {
        let row = value.downcast::<PyDict>()?.copy()?;
        promote_fields(&row)?;
        merged.append(row)?;
    }

    let spot = l1_snapshot
        .getattr("spot")
        .ok()
        .and_then(|value| value.extract::<f64>().ok())
        .filter(|value| value.is_finite() && *value > 0.0)
        .unwrap_or_else(|| py_to_f64(l0_snapshot.get_item("spot").ok().flatten().as_ref()));
    let atm_iv = l1_snapshot
        .getattr("aggregates")
        .ok()
        .and_then(|agg| agg.getattr("atm_iv").ok())
        .and_then(|value| value.extract::<f64>().ok())
        .filter(|value| value.is_finite() && *value > 0.0)
        .unwrap_or(0.0);
    let ttm_seconds = l1_snapshot
        .getattr("ttm_seconds")
        .ok()
        .and_then(|value| value.extract::<f64>().ok())
        .filter(|value| value.is_finite() && *value > 0.0);
    let source_version = l1_snapshot
        .getattr("version")
        .ok()
        .and_then(|value| value.extract::<i64>().ok())
        .filter(|value| *value > 0)
        .unwrap_or_else(|| l0_snapshot.get_item("version").ok().flatten().and_then(|value| value.extract::<i64>().ok()).unwrap_or(0));
    let source_timestamp_utc = source_timestamp_utc(&l0_snapshot)?;
    let valid = !merged.is_empty() && spot > 0.0;
    let invalid_reason = if merged.is_empty() {
        Some(EMPTY_CHAIN_REASON.to_string())
    } else if spot <= 0.0 {
        Some(INVALID_SPOT_REASON.to_string())
    } else {
        None
    };

    logger(py)?.call_method1(
        "debug",
        (
            "[ActiveOptionsInput] source_version=%s source_ts=%s valid=%s chain_rows=%d promoted_gamma=%d promoted_vanna=%d promoted_iv=%d promoted_delta=%d spot=%.4f atm_iv=%.4f",
            source_version,
            source_timestamp_utc.clone(),
            valid,
            merged.len(),
            merged
                .iter()
                .filter(|row| row.downcast::<PyDict>().ok().and_then(|row| row.get_item("computed_gamma").ok().flatten()).is_some())
                .count(),
            merged
                .iter()
                .filter(|row| row.downcast::<PyDict>().ok().and_then(|row| row.get_item("computed_vanna").ok().flatten()).is_some())
                .count(),
            merged
                .iter()
                .filter(|row| row.downcast::<PyDict>().ok().and_then(|row| row.get_item("computed_iv").ok().flatten()).is_some())
                .count(),
            merged
                .iter()
                .filter(|row| row.downcast::<PyDict>().ok().and_then(|row| row.get_item("computed_delta").ok().flatten()).is_some())
                .count(),
            spot,
            atm_iv,
        ),
    )?;

    Ok(ActiveOptionsInputSnapshotData {
        chain: merged.unbind(),
        spot,
        atm_iv,
        ttm_seconds,
        source_version,
        source_timestamp_utc,
        valid,
        invalid_reason,
    })
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<ActiveOptionsInputSnapshotData>()?;
    module.add_function(wrap_pyfunction!(build_active_options_input_snapshot, module)?)?;
    Ok(())
}
