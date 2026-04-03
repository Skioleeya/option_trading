use super::common::{
    as_dict, as_list, get_attr_bool, get_attr_f64, get_attr_string, py_dict_get, py_to_f64,
    py_to_i64, py_to_string, round_to, DIRECTION_COLOR_BEARISH, DIRECTION_COLOR_BULLISH,
    DIRECTION_COLOR_NEUTRAL, FLOW_REASON_ALL_ENGINES, FLOW_REASON_MISSING_GAMMA,
    FLOW_REASON_MISSING_TURNOVER, FLOW_REASON_MISSING_VANNA, FLOW_STATE_DEGRADED,
    FLOW_STATE_LIVE, PLACEHOLDER_SIGNATURE_PREFIX, ROW_QUALITY_PLACEHOLDER, ROW_QUALITY_REAL,
    STRIKE_ROUND_DIGITS, MAX_CHAIN_VOLUME,
};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyModule};

fn normalize_option_type(row: &Bound<'_, PyDict>) -> String {
    let token = py_to_string(py_dict_get(row, "option_type").as_ref())
        .or_else(|| py_to_string(py_dict_get(row, "type").as_ref()))
        .unwrap_or_default()
        .trim()
        .to_uppercase();
    if matches!(token.as_str(), "CALL" | "C") {
        "CALL".to_string()
    } else if matches!(token.as_str(), "PUT" | "P") {
        "PUT".to_string()
    } else if py_to_i64(py_dict_get(row, "is_call").as_ref()) > 0 {
        "CALL".to_string()
    } else {
        "PUT".to_string()
    }
}

fn sanitize_volume(value: i64) -> i64 {
    if value < 0 || value > MAX_CHAIN_VOLUME {
        0
    } else {
        value
    }
}

fn flow_reason(output: &Bound<'_, PyAny>) -> (String, Option<String>) {
    let mut reasons = Vec::new();
    if !get_attr_bool(output, "engine_d_active", true) {
        reasons.push(FLOW_REASON_MISSING_GAMMA.to_string());
    }
    if !get_attr_bool(output, "engine_e_active", true) {
        reasons.push(FLOW_REASON_MISSING_VANNA.to_string());
    }
    if !get_attr_bool(output, "engine_g_active", true) {
        reasons.push(FLOW_REASON_MISSING_TURNOVER.to_string());
    }
    if reasons.is_empty() {
        (FLOW_STATE_LIVE.to_string(), None)
    } else if reasons.len() == 3 {
        (FLOW_STATE_DEGRADED.to_string(), Some(FLOW_REASON_ALL_ENGINES.to_string()))
    } else {
        (FLOW_STATE_DEGRADED.to_string(), Some(reasons[0].clone()))
    }
}

fn direction_from_amount(value: f64) -> &'static str {
    if value > 0.0 {
        "BULLISH"
    } else if value < 0.0 {
        "BEARISH"
    } else {
        "NEUTRAL"
    }
}

fn format_flow(value: f64) -> String {
    let absolute = value.abs();
    let sign = if value < 0.0 { "-" } else { "" };
    if absolute >= 1_000_000.0 {
        format!("{sign}${:.1}M", absolute / 1_000_000.0)
    } else if absolute >= 1_000.0 {
        format!("{sign}${:.0}K", absolute / 1_000.0)
    } else {
        format!("{sign}${}", absolute as i64)
    }
}

fn format_volume(volume: i64) -> String {
    if volume >= 1_000_000 {
        format!("{:.1}M", volume as f64 / 1_000_000.0)
    } else if volume >= 1_000 {
        format!("{:.0}K", volume as f64 / 1_000.0)
    } else {
        volume.to_string()
    }
}

pub(crate) fn normalize_and_filter_chain_impl(
    py: Python<'_>,
    chain: &Bound<'_, PyAny>,
    min_volume: i64,
) -> PyResult<Py<PyList>> {
    let out = PyList::empty(py);
    for row in as_list(chain)?.iter() {
        let row = as_dict(&row)?;
        let normalized = PyDict::new(py);
        for (key, value) in row.iter() {
            normalized.set_item(key, value)?;
        }
        normalized.set_item("option_type", normalize_option_type(&row))?;
        let strike = py_to_f64(py_dict_get(&row, "strike").as_ref())
            .max(py_to_f64(py_dict_get(&row, "strike_price").as_ref()));
        normalized.set_item("strike", strike.max(0.0))?;

        let mut volume = sanitize_volume(py_to_i64(py_dict_get(&row, "volume").as_ref()));
        let current_volume = sanitize_volume(
            py_to_i64(py_dict_get(&row, "current_volume").as_ref())
                .max(py_to_i64(py_dict_get(&row, "currentVolume").as_ref()))
                .max(py_to_i64(py_dict_get(&row, "vol").as_ref())),
        );
        if volume <= 0 && current_volume > 0 {
            volume = current_volume;
        }
        normalized.set_item("volume", volume)?;
        normalized.set_item("current_volume", current_volume as f64)?;

        normalized.set_item(
            "turnover",
            py_to_f64(py_dict_get(&row, "turnover").as_ref())
                .max(py_to_f64(py_dict_get(&row, "amount").as_ref()))
                .max(py_to_f64(py_dict_get(&row, "trade_amount").as_ref()))
                .max(py_to_f64(py_dict_get(&row, "total_turnover").as_ref())),
        )?;
        normalized.set_item(
            "open_interest",
            py_to_i64(py_dict_get(&row, "open_interest").as_ref())
                .max(py_to_i64(py_dict_get(&row, "openInterest").as_ref()))
                .max(py_to_i64(py_dict_get(&row, "oi").as_ref())),
        )?;
        normalized.set_item(
            "last_price",
            py_to_f64(py_dict_get(&row, "last_price").as_ref())
                .max(py_to_f64(py_dict_get(&row, "last_done").as_ref()))
                .max(py_to_f64(py_dict_get(&row, "price").as_ref()))
                .max(py_to_f64(py_dict_get(&row, "mark_price").as_ref())),
        )?;
        normalized.set_item(
            "implied_volatility",
            py_to_f64(py_dict_get(&row, "computed_iv").as_ref())
                .max(py_to_f64(py_dict_get(&row, "implied_volatility").as_ref()))
                .max(py_to_f64(py_dict_get(&row, "iv").as_ref())),
        )?;
        normalized.set_item(
            "historical_volatility",
            py_to_f64(py_dict_get(&row, "historical_volatility").as_ref())
                .max(py_to_f64(py_dict_get(&row, "hv").as_ref()))
                .max(py_to_f64(py_dict_get(&row, "historical_volatility_decimal").as_ref())),
        )?;
        normalized.set_item(
            "delta",
            py_to_f64(py_dict_get(&row, "computed_delta").as_ref())
                .max(py_to_f64(py_dict_get(&row, "delta").as_ref())),
        )?;
        normalized.set_item(
            "gamma",
            py_to_f64(py_dict_get(&row, "computed_gamma").as_ref())
                .max(py_to_f64(py_dict_get(&row, "gamma").as_ref())),
        )?;
        normalized.set_item(
            "vanna",
            py_to_f64(py_dict_get(&row, "computed_vanna").as_ref())
                .max(py_to_f64(py_dict_get(&row, "vanna").as_ref())),
        )?;
        if volume >= min_volume {
            out.append(normalized)?;
        }
    }
    Ok(out.unbind())
}

#[pyfunction]
#[pyo3(signature = (*, chain, min_volume))]
fn active_options_normalize_and_filter_chain(
    py: Python<'_>,
    chain: &Bound<'_, PyAny>,
    min_volume: i64,
) -> PyResult<Py<PyList>> {
    normalize_and_filter_chain_impl(py, chain, min_volume)
}

#[pyfunction]
fn active_options_rank_outputs(py: Python<'_>, outputs: &Bound<'_, PyAny>) -> PyResult<Py<PyList>> {
    let mut rows: Vec<Py<PyAny>> = as_list(outputs)?.iter().map(|item| item.unbind()).collect();
    rows.sort_by(|left, right| {
        let left = left.bind(py);
        let right = right.bind(py);
        let left_live_rank = if get_attr_bool(&left, "engine_d_active", true)
            && get_attr_bool(&left, "engine_e_active", true)
            && get_attr_bool(&left, "engine_g_active", true)
        {
            0
        } else {
            1
        };
        let right_live_rank = if get_attr_bool(&right, "engine_d_active", true)
            && get_attr_bool(&right, "engine_e_active", true)
            && get_attr_bool(&right, "engine_g_active", true)
        {
            0
        } else {
            1
        };
        (
            left_live_rank,
            -(get_attr_f64(&left, "volume") as i64),
            -((get_attr_f64(&left, "turnover") * 100.0) as i64),
            -((get_attr_f64(&left, "impact_index") * 1000.0) as i64),
            get_attr_string(&left, "symbol", ""),
            (get_attr_f64(&left, "strike") * 10_000.0) as i64,
            get_attr_string(&left, "option_type", ""),
        )
            .cmp(&(
                right_live_rank,
                -(get_attr_f64(&right, "volume") as i64),
                -((get_attr_f64(&right, "turnover") * 100.0) as i64),
                -((get_attr_f64(&right, "impact_index") * 1000.0) as i64),
                get_attr_string(&right, "symbol", ""),
                (get_attr_f64(&right, "strike") * 10_000.0) as i64,
                get_attr_string(&right, "option_type", ""),
            ))
    });
    Ok(PyList::new(py, rows)?.unbind())
}

#[pyfunction]
fn active_options_format_row(py: Python<'_>, output: &Bound<'_, PyAny>, slot_index: i64) -> PyResult<Py<PyDict>> {
    let flow = get_attr_f64(output, "flow_d") + get_attr_f64(output, "flow_e") + get_attr_f64(output, "flow_g");
    let direction = direction_from_amount(flow);
    let (signal_state, signal_reason) = flow_reason(output);
    let glow = if get_attr_bool(output, "is_sweep", false) {
        "shadow-[0_0_15px_rgba(255,255,255,0.7)] animate-pulse"
    } else {
        match get_attr_string(output, "flow_intensity", "LOW").as_str() {
            "EXTREME" => "shadow-[0_0_12px_rgba(255,77,79,0.6)] animate-pulse",
            "HIGH" => "shadow-[0_0_8px_rgba(255,77,79,0.35)]",
            _ => "",
        }
    };
    let row = PyDict::new(py);
    row.set_item("symbol", "SPY")?;
    row.set_item("contract_symbol", get_attr_string(output, "symbol", "SPY"))?;
    row.set_item("option_type", get_attr_string(output, "option_type", "CALL"))?;
    row.set_item("strike", get_attr_f64(output, "strike"))?;
    row.set_item("implied_volatility", get_attr_f64(output, "implied_volatility"))?;
    row.set_item("volume", get_attr_f64(output, "volume") as i64)?;
    row.set_item("turnover", get_attr_f64(output, "turnover"))?;
    row.set_item("flow", flow)?;
    row.set_item("flow_score", get_attr_f64(output, "flow_deg"))?;
    row.set_item("impact_index", get_attr_f64(output, "impact_index"))?;
    row.set_item("is_sweep", get_attr_bool(output, "is_sweep", false))?;
    row.set_item("flow_deg_formatted", format_flow(flow))?;
    row.set_item("flow_volume_label", format_volume(get_attr_f64(output, "volume") as i64))?;
    row.set_item(
        "flow_color",
        match direction {
            "BULLISH" => DIRECTION_COLOR_BULLISH,
            "BEARISH" => DIRECTION_COLOR_BEARISH,
            _ => DIRECTION_COLOR_NEUTRAL,
        },
    )?;
    row.set_item("flow_glow", glow)?;
    row.set_item("flow_intensity", get_attr_string(output, "flow_intensity", "LOW"))?;
    row.set_item("flow_direction", direction)?;
    row.set_item("flow_d_z", round_to(get_attr_f64(output, "flow_d_z"), 3))?;
    row.set_item("flow_e_z", round_to(get_attr_f64(output, "flow_e_z"), 3))?;
    row.set_item("flow_g_z", round_to(get_attr_f64(output, "flow_g_z"), 3))?;
    row.set_item("is_placeholder", false)?;
    row.set_item("row_quality", ROW_QUALITY_REAL)?;
    row.set_item("fallback_reason", py.None())?;
    row.set_item("is_synthetic_fallback", false)?;
    row.set_item("flow_signal_state", signal_state)?;
    row.set_item("flow_signal_reason", signal_reason)?;
    row.set_item("slot_index", slot_index.max(1))?;
    Ok(row.unbind())
}

#[pyfunction]
fn active_options_placeholder_row(py: Python<'_>, slot_index: i64) -> PyResult<Py<PyDict>> {
    let row = PyDict::new(py);
    row.set_item("symbol", "—")?;
    row.set_item("contract_symbol", py.None())?;
    row.set_item("option_type", "CALL")?;
    row.set_item("strike", 0.0)?;
    row.set_item("implied_volatility", 0.0)?;
    row.set_item("volume", 0)?;
    row.set_item("turnover", 0.0)?;
    row.set_item("flow", 0.0)?;
    row.set_item("flow_score", 0.0)?;
    row.set_item("impact_index", 0.0)?;
    row.set_item("is_sweep", false)?;
    row.set_item("flow_deg_formatted", "—")?;
    row.set_item("flow_volume_label", "—")?;
    row.set_item("flow_color", DIRECTION_COLOR_NEUTRAL)?;
    row.set_item("flow_glow", "")?;
    row.set_item("flow_intensity", "LOW")?;
    row.set_item("flow_direction", "NEUTRAL")?;
    row.set_item("flow_d_z", 0.0)?;
    row.set_item("flow_e_z", 0.0)?;
    row.set_item("flow_g_z", 0.0)?;
    row.set_item("is_placeholder", true)?;
    row.set_item("row_quality", ROW_QUALITY_PLACEHOLDER)?;
    row.set_item("fallback_reason", py.None())?;
    row.set_item("is_synthetic_fallback", false)?;
    row.set_item("flow_signal_state", FLOW_STATE_DEGRADED)?;
    row.set_item("flow_signal_reason", FLOW_REASON_ALL_ENGINES)?;
    row.set_item("slot_index", slot_index.max(1))?;
    Ok(row.unbind())
}

#[pyfunction]
fn active_options_pad_rows(py: Python<'_>, rows: &Bound<'_, PyAny>, limit: i64) -> PyResult<Py<PyList>> {
    let target = limit.max(0) as usize;
    let out = PyList::empty(py);
    for (index, row) in as_list(rows)?.iter().enumerate().take(target) {
        let row = as_dict(&row)?.copy()?;
        row.set_item("slot_index", index + 1)?;
        if py_to_i64(row.get_item("is_placeholder")?.as_ref()) > 0 {
            row.set_item("row_quality", ROW_QUALITY_PLACEHOLDER)?;
            row.set_item("fallback_reason", py.None())?;
            row.set_item("is_synthetic_fallback", false)?;
            row.set_item("flow_signal_state", FLOW_STATE_DEGRADED)?;
            row.set_item("flow_signal_reason", FLOW_REASON_ALL_ENGINES)?;
        }
        out.append(row)?;
    }
    while out.len() < target {
        out.append(active_options_placeholder_row(py, (out.len() + 1) as i64)?.bind(py))?;
    }
    Ok(out.unbind())
}

#[pyfunction]
fn active_options_build_ranked_candidate(
    py: Python<'_>,
    outputs: &Bound<'_, PyAny>,
    limit: i64,
) -> PyResult<(Py<PyList>, Vec<(String, String, f64)>)> {
    let target = limit.max(0) as usize;
    let ranked_binding = active_options_rank_outputs(py, outputs)?;
    let ranked = ranked_binding.bind(py);
    let rows = PyList::empty(py);
    let mut signature = Vec::new();
    for (index, output) in ranked.iter().enumerate().take(target) {
        rows.append(active_options_format_row(py, &output, (index + 1) as i64)?.bind(py))?;
        signature.push((
            get_attr_string(&output, "symbol", ""),
            get_attr_string(&output, "option_type", "CALL"),
            round_to(get_attr_f64(&output, "strike"), STRIKE_ROUND_DIGITS),
        ));
    }
    while signature.len() < target {
        signature.push((
            format!("{PLACEHOLDER_SIGNATURE_PREFIX}{}", signature.len() + 1),
            "CALL".to_string(),
            0.0,
        ));
    }
    Ok((active_options_pad_rows(py, rows.as_any(), limit)?, signature))
}

#[pyfunction]
fn active_options_is_placeholder_signature(signature: Vec<(String, String, f64)>) -> bool {
    !signature.is_empty()
        && signature
            .iter()
            .all(|(symbol, _, _)| symbol.starts_with(PLACEHOLDER_SIGNATURE_PREFIX))
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(active_options_normalize_and_filter_chain, module)?)?;
    module.add_function(wrap_pyfunction!(active_options_rank_outputs, module)?)?;
    module.add_function(wrap_pyfunction!(active_options_format_row, module)?)?;
    module.add_function(wrap_pyfunction!(active_options_placeholder_row, module)?)?;
    module.add_function(wrap_pyfunction!(active_options_pad_rows, module)?)?;
    module.add_function(wrap_pyfunction!(active_options_build_ranked_candidate, module)?)?;
    module.add_function(wrap_pyfunction!(active_options_is_placeholder_signature, module)?)?;
    Ok(())
}
