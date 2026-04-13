use super::common::{
    as_dict, as_list, py_to_bool, py_to_f64, py_to_i64, FALLBACK_REASON_HARD_CHAIN,
    FALLBACK_REASON_SUBTHRESHOLD, FALLBACK_REASON_TURNOVER_OI, FLOW_REASON_ALL_ENGINES,
    FLOW_STATE_DEGRADED, ROW_QUALITY_REAL, ROW_QUALITY_SYNTHETIC, STRIKE_ROUND_DIGITS,
};
use super::support::normalize_and_filter_chain_impl;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyModule};

fn row_signature_key(row: &Bound<'_, PyDict>) -> (String, String, i64) {
    (
        row.get_item("symbol")
            .ok()
            .flatten()
            .and_then(|value| value.extract::<String>().ok())
            .unwrap_or_default(),
        row.get_item("option_type")
            .ok()
            .flatten()
            .and_then(|value| value.extract::<String>().ok())
            .unwrap_or_else(|| "CALL".to_string()),
        (py_to_f64(row.get_item("strike").ok().flatten().as_ref()) * 10_f64.powi(STRIKE_ROUND_DIGITS))
            .round() as i64,
    )
}

fn rank_rows(py: Python<'_>, rows: Vec<Py<PyAny>>) -> PyResult<Py<PyList>> {
    let mut values = rows;
    values.sort_by(|left, right| {
        let left = left.bind(py).downcast::<PyDict>().unwrap();
        let right = right.bind(py).downcast::<PyDict>().unwrap();
        (
            -py_to_i64(left.get_item("volume").ok().flatten().as_ref()),
            -((py_to_f64(left.get_item("turnover").ok().flatten().as_ref()) * 100.0) as i64),
            -py_to_i64(left.get_item("open_interest").ok().flatten().as_ref()),
            left.get_item("symbol").ok().flatten().and_then(|v| v.extract::<String>().ok()).unwrap_or_default(),
        )
            .cmp(&(
                -py_to_i64(right.get_item("volume").ok().flatten().as_ref()),
                -((py_to_f64(right.get_item("turnover").ok().flatten().as_ref()) * 100.0) as i64),
                -py_to_i64(right.get_item("open_interest").ok().flatten().as_ref()),
                right.get_item("symbol").ok().flatten().and_then(|v| v.extract::<String>().ok()).unwrap_or_default(),
            ))
    });
    Ok(PyList::new(py, values)?.unbind())
}

fn with_synthetic_volume(row: &Bound<'_, PyDict>, force_minimum: bool) -> PyResult<Py<PyDict>> {
    let updated = row.copy()?;
    let volume = py_to_i64(updated.get_item("volume")?.as_ref());
    if volume > 0 {
        return Ok(updated.unbind());
    }
    let turnover = py_to_f64(updated.get_item("turnover")?.as_ref());
    if turnover <= 0.0 {
        if py_to_i64(updated.get_item("open_interest")?.as_ref()) > 0 || force_minimum {
            updated.set_item("volume", 1)?;
        }
        return Ok(updated.unbind());
    }
    let last_price = py_to_f64(updated.get_item("last_price")?.as_ref());
    let inferred = if last_price > 0.0 {
        (turnover / (last_price * 100.0).max(1e-6)).floor() as i64
    } else {
        1
    };
    updated.set_item("volume", inferred.max(1))?;
    Ok(updated.unbind())
}

#[pyfunction]
#[pyo3(signature = (*, chain, max_candidates))]
fn active_options_fallback_candidates_when_empty(
    py: Python<'_>,
    chain: &Bound<'_, PyAny>,
    max_candidates: i64,
) -> PyResult<(Py<PyList>, String)> {
    let target = max_candidates.max(0) as usize;
    if target == 0 {
        return Ok((PyList::empty(py).unbind(), "none".to_string()));
    }
    let normalized = normalize_and_filter_chain_impl(py, chain, 1.0, i64::MAX)?;
    let normalized = normalized.bind(py);

    let mut positive: Vec<Py<PyAny>> = Vec::new();
    for row in normalized.iter() {
        if py_to_i64(row.downcast::<PyDict>()?.get_item("volume").ok().flatten().as_ref()) > 0 {
            positive.push(row.unbind());
        }
    }
    if !positive.is_empty() {
        let selected = PyList::empty(py);
        for row in rank_rows(py, positive)?.bind(py).iter().take(target) {
            selected.append(row)?;
        }
        return Ok((selected.unbind(), FALLBACK_REASON_SUBTHRESHOLD.to_string()));
    }

    let mut eligible: Vec<Py<PyAny>> = Vec::new();
    for row in normalized.iter() {
        let row = row.downcast::<PyDict>()?;
        if py_to_f64(row.get_item("turnover").ok().flatten().as_ref()) > 0.0
            || py_to_i64(row.get_item("open_interest").ok().flatten().as_ref()) > 0
        {
            eligible.push(row.clone().unbind().into());
        }
    }
    if !eligible.is_empty() {
        let selected = PyList::empty(py);
        for row in rank_rows(py, eligible)?.bind(py).iter().take(target) {
            selected.append(with_synthetic_volume(row.downcast::<PyDict>()?, false)?.bind(py))?;
        }
        return Ok((selected.unbind(), FALLBACK_REASON_TURNOVER_OI.to_string()));
    }

    let selected = PyList::empty(py);
    let mut normalized_rows: Vec<Py<PyAny>> = Vec::new();
    for row in normalized.iter() {
        normalized_rows.push(row.unbind());
    }
    for row in rank_rows(py, normalized_rows)?
        .bind(py)
        .iter()
        .take(target)
    {
        selected.append(with_synthetic_volume(row.downcast::<PyDict>()?, true)?.bind(py))?;
    }
    Ok((selected.unbind(), FALLBACK_REASON_HARD_CHAIN.to_string()))
}

#[pyfunction]
#[pyo3(signature = (*, filtered, chain, target_limit))]
fn active_options_supplement_partial_candidates(
    py: Python<'_>,
    filtered: &Bound<'_, PyAny>,
    chain: &Bound<'_, PyAny>,
    target_limit: i64,
) -> PyResult<(Py<PyList>, Option<String>, Vec<(String, String, f64)>)> {
    let missing = target_limit.max(0) as usize - as_list(filtered)?.len();
    if missing == 0 {
        return Ok((as_list(filtered)?.unbind(), None, Vec::new()));
    }
    let out = PyList::empty(py);
    let mut existing = std::collections::HashSet::new();
    for row in as_list(filtered)?.iter() {
        let row = as_dict(&row)?;
        existing.insert(row_signature_key(&row));
        out.append(row.copy()?)?;
    }
    let normalized_chain = normalize_and_filter_chain_impl(py, chain, 1.0, i64::MAX)?;
    let remainder = PyList::empty(py);
    for row in normalized_chain.bind(py).iter() {
        let row = row.downcast::<PyDict>()?;
        if existing.contains(&row_signature_key(row)) {
            continue;
        }
        remainder.append(row.copy()?)?;
    }
    let (fallback_rows, mode) =
        active_options_fallback_candidates_when_empty(py, remainder.as_any(), missing as i64)?;
    let mut added_keys = Vec::new();
    let mut added = Vec::new();
    for row in fallback_rows.bind(py).iter() {
        let row = row.downcast::<PyDict>()?;
        let signature_key = row_signature_key(row);
        if existing.contains(&signature_key) || added_keys.contains(&signature_key) {
            continue;
        }
        added_keys.push(signature_key);
        added.push((
            row.get_item("symbol")?.and_then(|value| value.extract::<String>().ok()).unwrap_or_default(),
            row.get_item("option_type")?.and_then(|value| value.extract::<String>().ok()).unwrap_or_else(|| "CALL".to_string()),
            py_to_f64(row.get_item("strike")?.as_ref()),
        ));
        out.append(row.copy()?)?;
        if added.len() >= missing {
            break;
        }
    }
    Ok((out.unbind(), if added.is_empty() { None } else { Some(mode) }, added))
}

#[pyfunction]
#[pyo3(signature = (*, filtered, limit))]
fn active_options_build_neutral_outputs_from_chain(
    py: Python<'_>,
    filtered: &Bound<'_, PyAny>,
    limit: i64,
) -> PyResult<Py<PyList>> {
    let out = PyList::empty(py);
    for row in rank_rows(py, as_list(filtered)?.iter().map(|item| item.unbind()).collect())?
        .bind(py)
        .iter()
        .take(limit.max(0) as usize)
    {
        let row = row.downcast::<PyDict>()?;
        let kwargs = PyDict::new(py);
        kwargs.set_item("symbol", row.get_item("symbol")?.unwrap_or_else(|| "SPY".into_pyobject(py).unwrap().into_any()))?;
        kwargs.set_item("option_type", row.get_item("option_type")?.unwrap_or_else(|| "CALL".into_pyobject(py).unwrap().into_any()))?;
        kwargs.set_item("strike", py_to_f64(row.get_item("strike")?.as_ref()))?;
        kwargs.set_item("implied_volatility", py_to_f64(row.get_item("implied_volatility")?.as_ref()))?;
        kwargs.set_item("volume", py_to_i64(row.get_item("volume")?.as_ref()))?;
        kwargs.set_item("turnover", py_to_f64(row.get_item("turnover")?.as_ref()))?;
        kwargs.set_item("flow_d", 0.0)?;
        kwargs.set_item("flow_e", 0.0)?;
        kwargs.set_item("flow_g", 0.0)?;
        kwargs.set_item("flow_d_z", 0.0)?;
        kwargs.set_item("flow_e_z", 0.0)?;
        kwargs.set_item("flow_g_z", 0.0)?;
        kwargs.set_item("flow_deg", 0.0)?;
        kwargs.set_item("impact_index", 0.0)?;
        kwargs.set_item("is_sweep", false)?;
        kwargs.set_item("flow_direction", "NEUTRAL")?;
        kwargs.set_item("flow_intensity", "LOW")?;
        kwargs.set_item("engine_d_active", false)?;
        kwargs.set_item("engine_e_active", false)?;
        kwargs.set_item("engine_g_active", false)?;
        out.append(py.import("shared_rust.models")?.getattr("FlowEngineOutput")?.call((), Some(&kwargs))?)?;
    }
    Ok(out.unbind())
}

#[pyfunction]
#[pyo3(signature = (rows, *, fallback_reason))]
fn active_options_mark_rows_as_synthetic_fallback(
    py: Python<'_>,
    rows: &Bound<'_, PyAny>,
    fallback_reason: &str,
) -> PyResult<Py<PyList>> {
    let out = PyList::empty(py);
    for row in as_list(rows)?.iter() {
        let row = as_dict(&row)?.copy()?;
        if py_to_bool(row.get_item("is_placeholder")?.as_ref(), false) {
            row.set_item("row_quality", "PLACEHOLDER")?;
            row.set_item("fallback_reason", py.None())?;
            row.set_item("is_synthetic_fallback", false)?;
            row.set_item("flow_signal_state", FLOW_STATE_DEGRADED)?;
            row.set_item("flow_signal_reason", FLOW_REASON_ALL_ENGINES)?;
        } else {
            row.set_item("row_quality", ROW_QUALITY_SYNTHETIC)?;
            row.set_item("fallback_reason", fallback_reason)?;
            row.set_item("is_synthetic_fallback", true)?;
            row.set_item("flow_signal_state", FLOW_STATE_DEGRADED)?;
            if row.get_item("flow_signal_reason")?.is_none() {
                row.set_item("flow_signal_reason", fallback_reason)?;
            }
        }
        out.append(row)?;
    }
    Ok(out.unbind())
}

#[pyfunction]
#[pyo3(signature = (rows, *, fallback_reason, signatures))]
fn active_options_mark_rows_with_fallback_signatures(
    py: Python<'_>,
    rows: &Bound<'_, PyAny>,
    fallback_reason: &str,
    signatures: Vec<(String, String, f64)>,
) -> PyResult<Py<PyList>> {
    let signature_set: std::collections::HashSet<_> = signatures
        .into_iter()
        .map(|(symbol, option_type, strike)| {
            (
                symbol,
                option_type,
                (strike * 10_f64.powi(STRIKE_ROUND_DIGITS)).round() as i64,
            )
        })
        .collect();
    let out = PyList::empty(py);
    for row in as_list(rows)?.iter() {
        let row = as_dict(&row)?.copy()?;
        if py_to_bool(row.get_item("is_placeholder")?.as_ref(), false) {
            out.append(row)?;
            continue;
        }
        let signature = (
            row.get_item("contract_symbol")?
                .or_else(|| row.get_item("symbol").ok().flatten())
                .and_then(|value| value.extract::<String>().ok())
                .unwrap_or_default(),
            row.get_item("option_type")?
                .and_then(|value| value.extract::<String>().ok())
                .unwrap_or_else(|| "CALL".to_string()),
            (py_to_f64(row.get_item("strike")?.as_ref()) * 10_f64.powi(STRIKE_ROUND_DIGITS)).round() as i64,
        );
        if signature_set.contains(&signature) {
            row.set_item("fallback_reason", fallback_reason)?;
            if fallback_reason == FALLBACK_REASON_SUBTHRESHOLD {
                row.set_item("row_quality", ROW_QUALITY_REAL)?;
                row.set_item("is_synthetic_fallback", false)?;
            } else {
                row.set_item("row_quality", ROW_QUALITY_SYNTHETIC)?;
                row.set_item("is_synthetic_fallback", true)?;
                row.set_item("flow_signal_state", FLOW_STATE_DEGRADED)?;
                if row.get_item("flow_signal_reason")?.is_none() {
                    row.set_item("flow_signal_reason", fallback_reason)?;
                }
            }
        }
        out.append(row)?;
    }
    Ok(out.unbind())
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(active_options_fallback_candidates_when_empty, module)?)?;
    module.add_function(wrap_pyfunction!(active_options_supplement_partial_candidates, module)?)?;
    module.add_function(wrap_pyfunction!(active_options_build_neutral_outputs_from_chain, module)?)?;
    module.add_function(wrap_pyfunction!(active_options_mark_rows_as_synthetic_fallback, module)?)?;
    module.add_function(wrap_pyfunction!(active_options_mark_rows_with_fallback_signatures, module)?)?;
    Ok(())
}
