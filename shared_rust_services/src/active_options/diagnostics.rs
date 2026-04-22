use super::common::{
    as_list, py_to_bool, py_to_string, FLOW_REASON_MISSING_GAMMA, FLOW_REASON_MISSING_TURNOVER,
    FLOW_STATE_DEGRADED, FLOW_STATE_LIVE, ROW_QUALITY_SYNTHETIC,
};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyModule};

#[pyfunction]
#[pyo3(signature = (*, latest_rows, empty_filter_count=0, last_empty_filter_at_utc=None, empty_filter_fallback_count=0, last_empty_filter_fallback_at_utc=None, partial_fallback_count=0, last_partial_fallback_at_utc=None, last_partial_fallback_mode=None, filtered_candidates_count=0, supplemented_rows=0, engine_empty_output_fallback_count=0, last_engine_empty_output_fallback_at_utc=None, last_fallback_mode=None, last_update_at_utc=None, empty_filter_fallback_enabled=true, empty_filter_fallback_max_candidates=120))]
fn active_options_build_runtime_diagnostics(
    py: Python<'_>,
    latest_rows: &Bound<'_, PyAny>,
    empty_filter_count: i64,
    last_empty_filter_at_utc: Option<String>,
    empty_filter_fallback_count: i64,
    last_empty_filter_fallback_at_utc: Option<String>,
    partial_fallback_count: i64,
    last_partial_fallback_at_utc: Option<String>,
    last_partial_fallback_mode: Option<String>,
    filtered_candidates_count: i64,
    supplemented_rows: i64,
    engine_empty_output_fallback_count: i64,
    last_engine_empty_output_fallback_at_utc: Option<String>,
    last_fallback_mode: Option<String>,
    last_update_at_utc: Option<String>,
    empty_filter_fallback_enabled: bool,
    empty_filter_fallback_max_candidates: i64,
) -> PyResult<Py<PyDict>> {
    let rows = as_list(latest_rows)?;
    let total = rows.len() as i64;
    let placeholders = rows
        .iter()
        .filter(|row| py_to_bool(row.downcast::<PyDict>().unwrap().get_item("is_placeholder").ok().flatten().as_ref(), false))
        .count() as i64;
    let synthetic = rows
        .iter()
        .filter(|row| {
            row.downcast::<PyDict>()
                .ok()
                .and_then(|dict| dict.get_item("row_quality").ok().flatten())
                .and_then(|value| value.extract::<String>().ok())
                .map(|value| value == ROW_QUALITY_SYNTHETIC)
                .unwrap_or(false)
        })
        .count() as i64;
    let degraded = rows
        .iter()
        .filter(|row| {
            py_to_string(
                row.downcast::<PyDict>()
                    .unwrap()
                    .get_item("flow_signal_state")
                    .ok()
                    .flatten()
                    .as_ref(),
            )
            .as_deref()
                == Some(FLOW_STATE_DEGRADED)
        })
        .count() as i64;
    let live = rows
        .iter()
        .filter(|row| {
            py_to_string(
                row.downcast::<PyDict>()
                    .unwrap()
                    .get_item("flow_signal_state")
                    .ok()
                    .flatten()
                    .as_ref(),
            )
            .as_deref()
                == Some(FLOW_STATE_LIVE)
        })
        .count() as i64;
    let missing_gamma = rows
        .iter()
        .filter(|row| {
            py_to_string(
                row.downcast::<PyDict>()
                    .unwrap()
                    .get_item("flow_signal_reason")
                    .ok()
                    .flatten()
                    .as_ref(),
            )
            .as_deref()
                == Some(FLOW_REASON_MISSING_GAMMA)
        })
        .count() as i64;
    let missing_turnover = rows
        .iter()
        .filter(|row| {
            py_to_string(
                row.downcast::<PyDict>()
                    .unwrap()
                    .get_item("flow_signal_reason")
                    .ok()
                    .flatten()
                    .as_ref(),
            )
            .as_deref()
                == Some(FLOW_REASON_MISSING_TURNOVER)
        })
        .count() as i64;

    let out = PyDict::new(py);
    out.set_item("rows_total", total)?;
    out.set_item("rows_placeholder", placeholders)?;
    out.set_item("rows_real", total - placeholders)?;
    out.set_item("rows_real_non_synthetic", total - placeholders - synthetic)?;
    out.set_item("rows_synthetic_fallback", synthetic)?;
    out.set_item("degraded_rows", degraded)?;
    out.set_item("live_rows", live)?;
    out.set_item("missing_gamma_rows", missing_gamma)?;
    out.set_item("missing_turnover_rows", missing_turnover)?;
    out.set_item("all_placeholder", total > 0 && total == placeholders)?;
    out.set_item("empty_filter_count", empty_filter_count)?;
    out.set_item("last_empty_filter_at_utc", last_empty_filter_at_utc)?;
    out.set_item("empty_filter_fallback_count", empty_filter_fallback_count)?;
    out.set_item("last_empty_filter_fallback_at_utc", last_empty_filter_fallback_at_utc)?;
    out.set_item("partial_fallback_count", partial_fallback_count)?;
    out.set_item("last_partial_fallback_at_utc", last_partial_fallback_at_utc)?;
    out.set_item("last_partial_fallback_mode", last_partial_fallback_mode)?;
    out.set_item("filtered_candidates_count", filtered_candidates_count)?;
    out.set_item("supplemented_rows", supplemented_rows)?;
    out.set_item("engine_empty_output_fallback_count", engine_empty_output_fallback_count)?;
    out.set_item("last_engine_empty_output_fallback_at_utc", last_engine_empty_output_fallback_at_utc)?;
    out.set_item("last_fallback_mode", last_fallback_mode)?;
    out.set_item("last_update_at_utc", last_update_at_utc)?;
    out.set_item("empty_filter_fallback_enabled", empty_filter_fallback_enabled)?;
    out.set_item("empty_filter_fallback_max_candidates", empty_filter_fallback_max_candidates)?;
    Ok(out.unbind())
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(active_options_build_runtime_diagnostics, module)?)?;
    Ok(())
}
