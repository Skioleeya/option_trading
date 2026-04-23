use crate::research_store_support::{
    direction_to_code, gex_intensity_to_code, iv_regime_to_code, l0_rust, parse_ts_any,
    shared_services, utc_iso,
};
use crate::tactical::compute_vrp_impl;
use chrono::{DateTime, Utc};
use pyo3::{exceptions::PyValueError, prelude::*, types::PyDict};

pub(crate) fn parse_append_inputs(
    py: Python<'_>,
    decision: &Bound<'_, PyAny>,
    snapshot: &Bound<'_, PyAny>,
    payload: &Bound<'_, PyAny>,
) -> PyResult<(Py<PyAny>, DateTime<Utc>, f64, i64)> {
    let ts = required_timestamp(payload, "payload.data_timestamp")?;
    let spot = required_positive_spot(snapshot, payload)?;
    let (row, l0_version) = build_canonical_row(py, decision, snapshot, payload, ts, spot)?;
    Ok((row, ts, spot, l0_version))
}

pub(crate) fn feature_fields_only(py: Python<'_>) -> PyResult<Vec<String>> {
    shared_services(py)?
        .getattr("research_feature_fields")?
        .call0()?
        .extract::<Vec<String>>()
}

fn build_canonical_row(
    py: Python<'_>,
    decision: &Bound<'_, PyAny>,
    snapshot: &Bound<'_, PyAny>,
    payload: &Bound<'_, PyAny>,
    ts: DateTime<Utc>,
    spot: f64,
) -> PyResult<(Py<PyAny>, i64)> {
    let l0_version = required_i64_attr(snapshot, "version", "snapshot.version")?;
    let aggregates = snapshot.getattr("aggregates")?;
    let micro = snapshot.getattr("microstructure")?;
    let atm_iv = required_finite_attr(&aggregates, "atm_iv", "snapshot.aggregates.atm_iv")?;
    let feature_vector = decision
        .getattr("feature_vector")
        .ok()
        .and_then(|value| value.downcast_into::<PyDict>().ok());
    let mm_flow = payload
        .getattr("fused_signal")?
        .downcast_into::<PyDict>()
        .ok()
        .and_then(|dict| dict.get_item("mm_flow").ok().flatten())
        .and_then(|value| value.downcast_into::<PyDict>().ok())
        .ok_or_else(|| PyValueError::new_err("payload.fused_signal.mm_flow missing or invalid"))?;
    let native = l0_rust(py)?;
    let row = PyDict::new(py);
    row.set_item("data_timestamp", utc_iso(ts))?;
    row.set_item("as_of_utc", utc_iso(ts))?;
    row.set_item("l0_version", l0_version)?;
    row.set_item("symbol", "SPY")?;
    row.set_item("spot", spot)?;
    for key in ["atm_iv", "net_gex", "call_wall", "put_wall", "flip_level"] {
        row.set_item(
            key,
            required_finite_attr(&aggregates, key, &format!("snapshot.aggregates.{key}"))?,
        )?;
    }
    row.set_item(
        "bbo_imbalance_raw",
        required_finite_attr(
            &micro,
            "bbo_imbalance_raw",
            "snapshot.microstructure.bbo_imbalance_raw",
        )?,
    )?;
    row.set_item(
        "session_phase",
        required_str_attr(&micro, "session_phase", "snapshot.microstructure.session_phase")?,
    )?;
    for key in [
        "skew_25d_normalized",
        "rr25_call_minus_put",
        "realized_volatility_15m",
        "vol_risk_premium",
        "vrp_realized_based",
    ] {
        row.set_item(key, optional_feature_f64(feature_vector.as_ref(), key, "decision.feature_vector")?)?;
    }
    let diagnostics = snapshot
        .getattr("extra_metadata")?
        .downcast_into::<PyDict>()
        .ok()
        .and_then(|dict| dict.get_item("longport_option_diagnostics").ok().flatten())
        .unwrap_or_else(|| PyDict::new(py).into_any());
    let longport = native
        .call_method1("service_research_longport_columns", (diagnostics,))?
        .downcast_into::<PyDict>()?;
    let official_hv = optional_dict_f64(&longport, "longport_official_hv_decimal", "longport diagnostics")?;
    row.set_item("longport_official_hv_decimal", official_hv)?;
    row.set_item(
        "longport_official_hv_sample_count",
        longport
            .get_item("longport_official_hv_sample_count")
            .ok()
            .flatten()
            .and_then(|value| value.extract::<i64>().ok())
            .unwrap_or(0),
    )?;
    row.set_item(
        "longport_official_hv_age_sec",
        optional_dict_f64(&longport, "longport_official_hv_age_sec", "longport diagnostics")?,
    )?;
    row.set_item(
        "vrp_official_hv_based",
        official_hv.filter(|hv| *hv > 0.0).and_then(|hv| compute_vrp_impl(Some(atm_iv), Some(hv))),
    )?;
    row.set_item(
        "direction_code",
        direction_to_code(&required_str_attr(decision, "direction", "decision.direction")?),
    )?;
    row.set_item(
        "iv_regime_code",
        iv_regime_to_code(&required_str_attr(decision, "iv_regime", "decision.iv_regime")?),
    )?;
    row.set_item(
        "gex_intensity_code",
        gex_intensity_to_code(&required_str_attr(decision, "gex_intensity", "decision.gex_intensity")?),
    )?;
    row.set_item("confidence", required_finite_attr(decision, "confidence", "decision.confidence")?)?;
    row.set_item("max_impact", required_finite_attr(decision, "max_impact", "decision.max_impact")?)?;
    row.set_item(
        "dealer_squeeze_alert",
        required_bool_attr(&micro, "dealer_squeeze_alert", "snapshot.microstructure.dealer_squeeze_alert")?,
    )?;
    for key in [
        "net_delta_exposure_live",
        "net_gamma_exposure_live",
        "residual_delta_after_netting",
        "oi_participation_ratio_live",
        "flow_suppression_bias",
        "flow_dominance_ratio",
        "midpoint_tickrule_count",
        "condition_filtered_count",
        "complex_spread_count",
    ] {
        row.set_item(key, required_finite_dict_f64(&mm_flow, key, "payload.fused_signal.mm_flow")?)?;
    }
    row.set_item("stored_at", utc_iso(Utc::now()))?;
    for key in [
        "fwd_ret_1m",
        "fwd_ret_5m",
        "fwd_ret_15m",
        "fwd_ret_60m",
        "max_adverse_excursion",
        "realized_vol_horizon",
        "horizon_observed_seconds",
        "label_stored_at",
    ] {
        row.set_item(key, py.None())?;
    }
    Ok((row.unbind().into(), l0_version))
}

fn required_timestamp(obj: &Bound<'_, PyAny>, ctx: &str) -> PyResult<DateTime<Utc>> {
    let raw = obj
        .getattr("data_timestamp")
        .map_err(|_| PyValueError::new_err(format!("{ctx} missing")))?;
    parse_ts_any(&raw)?.ok_or_else(|| PyValueError::new_err(format!("{ctx} invalid")))
}

fn required_positive_spot(snapshot: &Bound<'_, PyAny>, payload: &Bound<'_, PyAny>) -> PyResult<f64> {
    let spot = snapshot
        .getattr("spot")
        .ok()
        .and_then(|value| value.extract::<f64>().ok())
        .or_else(|| payload.getattr("spot").ok().and_then(|value| value.extract::<f64>().ok()))
        .ok_or_else(|| PyValueError::new_err("snapshot.spot missing"))?;
    if !spot.is_finite() || spot <= 0.0 {
        return Err(PyValueError::new_err("snapshot.spot must be finite and > 0"));
    }
    Ok(spot)
}

fn required_finite_attr(obj: &Bound<'_, PyAny>, key: &str, ctx: &str) -> PyResult<f64> {
    let value = obj
        .getattr(key)
        .map_err(|_| PyValueError::new_err(format!("{ctx} missing")))?;
    let number = value
        .extract::<f64>()
        .map_err(|_| PyValueError::new_err(format!("{ctx} not float")))?;
    if !number.is_finite() {
        return Err(PyValueError::new_err(format!("{ctx} not finite")));
    }
    Ok(number)
}

fn required_i64_attr(obj: &Bound<'_, PyAny>, key: &str, ctx: &str) -> PyResult<i64> {
    obj.getattr(key)
        .map_err(|_| PyValueError::new_err(format!("{ctx} missing")))?
        .extract::<i64>()
        .map_err(|_| PyValueError::new_err(format!("{ctx} not int")))
}

fn required_str_attr(obj: &Bound<'_, PyAny>, key: &str, ctx: &str) -> PyResult<String> {
    let text = obj
        .getattr(key)
        .map_err(|_| PyValueError::new_err(format!("{ctx} missing")))?
        .extract::<String>()
        .map_err(|_| PyValueError::new_err(format!("{ctx} not string")))?;
    if text.trim().is_empty() {
        return Err(PyValueError::new_err(format!("{ctx} empty")));
    }
    Ok(text)
}

fn required_bool_attr(obj: &Bound<'_, PyAny>, key: &str, ctx: &str) -> PyResult<bool> {
    obj.getattr(key)
        .map_err(|_| PyValueError::new_err(format!("{ctx} missing")))?
        .extract::<bool>()
        .map_err(|_| PyValueError::new_err(format!("{ctx} not bool")))
}

fn optional_feature_f64(
    dict: Option<&Bound<'_, PyDict>>,
    key: &str,
    ctx: &str,
) -> PyResult<Option<f64>> {
    let Some(feature_dict) = dict else {
        return Ok(None);
    };
    optional_dict_f64(feature_dict, key, ctx)
}

fn optional_dict_f64(dict: &Bound<'_, PyDict>, key: &str, ctx: &str) -> PyResult<Option<f64>> {
    let Some(raw) = dict.get_item(key).ok().flatten() else {
        return Ok(None);
    };
    if raw.is_none() {
        return Ok(None);
    }
    let value = raw
        .extract::<f64>()
        .map_err(|_| PyValueError::new_err(format!("{ctx} key not float: {key}")))?;
    if !value.is_finite() {
        return Err(PyValueError::new_err(format!("{ctx} key not finite: {key}")));
    }
    Ok(Some(value))
}

fn required_finite_dict_f64(dict: &Bound<'_, PyDict>, key: &str, ctx: &str) -> PyResult<f64> {
    optional_dict_f64(dict, key, ctx)?
        .ok_or_else(|| PyValueError::new_err(format!("{ctx} missing key: {key}")))
}
