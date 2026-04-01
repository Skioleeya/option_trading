use pyo3::exceptions::PyKeyError;
use pyo3::prelude::*;
use pyo3::types::PyModule;

#[pyclass(frozen)]
#[derive(Clone)]
pub struct MetricSemantics {
    #[pyo3(get)]
    pub metric_name: &'static str,
    #[pyo3(get)]
    pub classification: &'static str,
    #[pyo3(get)]
    pub unit: &'static str,
    #[pyo3(get)]
    pub sign_convention: &'static str,
    #[pyo3(get)]
    pub data_prerequisites: &'static str,
    #[pyo3(get)]
    pub canonical_description: &'static str,
    #[pyo3(get)]
    pub live_usage: &'static str,
}

const METRIC_ROWS: [MetricSemantics; 14] = [
    MetricSemantics { metric_name: "net_gex", classification: "proxy", unit: "MMUSD", sign_convention: "positive = call gross proxy minus put gross proxy", data_prerequisites: "public option chain with gamma, OI, multiplier, spot", canonical_description: "OI-based net GEX structural proxy; not dealer inventory truth.", live_usage: "live" },
    MetricSemantics { metric_name: "zero_gamma_level", classification: "proxy", unit: "underlying price", sign_convention: "spot level where OI-based net GEX proxy crosses zero", data_prerequisites: "same prerequisites as net_gex plus spot-grid recomputation", canonical_description: "OI-based zero-gamma proxy derived from spot-grid recomputation.", live_usage: "live" },
    MetricSemantics { metric_name: "call_wall", classification: "proxy", unit: "underlying price", sign_convention: "strike with peak call-side GEX proxy", data_prerequisites: "per-strike call-side GEX proxy", canonical_description: "Trading-practice resistance proxy; not a unified academic wall definition.", live_usage: "live" },
    MetricSemantics { metric_name: "put_wall", classification: "proxy", unit: "underlying price", sign_convention: "strike with peak put-side GEX proxy", data_prerequisites: "per-strike put-side GEX proxy", canonical_description: "Trading-practice support proxy; not a unified academic wall definition.", live_usage: "live" },
    MetricSemantics { metric_name: "flip_level_cumulative", classification: "proxy", unit: "underlying price", sign_convention: "first strike where cumulative net GEX proxy crosses zero", data_prerequisites: "sorted per-strike cumulative net GEX proxy profile", canonical_description: "Trading-practice cumulative flip proxy; distinct from zero-gamma recomputation.", live_usage: "live" },
    MetricSemantics { metric_name: "FLOW_D", classification: "heuristic", unit: "signed flow score input", sign_convention: "positive = bullish call-side pressure proxy, negative = bearish put-side pressure proxy", data_prerequisites: "public volume, gamma proxy, spot", canonical_description: "Research heuristic combining public volume and gamma proxy; not a unified academic exact formula.", live_usage: "live" },
    MetricSemantics { metric_name: "FLOW_E", classification: "heuristic", unit: "signed flow score input", sign_convention: "sign follows IV premium/discount direction by option type", data_prerequisites: "public volume, vanna proxy, IV, HV", canonical_description: "Research heuristic combining vanna proxy and IV premium spread; not a unified academic exact formula.", live_usage: "live" },
    MetricSemantics { metric_name: "FLOW_G", classification: "heuristic", unit: "signed flow score input", sign_convention: "positive = call-side OI expansion proxy, negative = put-side OI expansion proxy", data_prerequisites: "public OI delta, IV, ATM IV, turnover", canonical_description: "Public-data proxy for OI momentum; not a unified academic exact formula.", live_usage: "live" },
    MetricSemantics { metric_name: "vol_risk_premium", classification: "proxy", unit: "% points", sign_convention: "ATM_IV(%) - baseline_HV(%)", data_prerequisites: "ATM IV and configured baseline HV", canonical_description: "Live proxy VRP based on configured baseline HV, not canonical realized-vol VRP.", live_usage: "live" },
    MetricSemantics { metric_name: "guard_vrp_proxy_pct", classification: "heuristic", unit: "% points", sign_convention: "ATM_IV(%) - realized_vol_proxy(%) derived from |vol_accel_ratio|", data_prerequisites: "ATM IV and vol_accel_ratio", canonical_description: "Guard-only VRP proxy used for veto hysteresis; not shared with live feature VRP.", live_usage: "live" },
    MetricSemantics { metric_name: "skew_25d_normalized", classification: "proxy", unit: "normalized skew ratio", sign_convention: "(put_iv - call_iv) / atm_iv using nearest ±25d legs", data_prerequisites: "ATM IV plus nearest ±25d legs", canonical_description: "Legacy normalized skew field retained for compatibility and research export.", live_usage: "legacy-only" },
    MetricSemantics { metric_name: "rr25_call_minus_put", classification: "proxy", unit: "IV points", sign_convention: "call_iv(+25d) - put_iv(-25d)", data_prerequisites: "nearest ±25d legs and valid delta gating", canonical_description: "Canonical 25d risk reversal used as the live skew source of truth.", live_usage: "live" },
    MetricSemantics { metric_name: "net_charm_raw_sum", classification: "proxy", unit: "raw Greek sum", sign_convention: "sum of per-contract charm sensitivities", data_prerequisites: "per-contract charm values across the chain", canonical_description: "Canonical raw chain sum of charm sensitivities; not position-weighted exposure.", live_usage: "live" },
    MetricSemantics { metric_name: "net_vanna_raw_sum", classification: "proxy", unit: "raw Greek sum", sign_convention: "sum of per-contract vanna sensitivities", data_prerequisites: "per-contract vanna values across the chain", canonical_description: "Canonical raw chain sum of vanna sensitivities; not position-weighted exposure.", live_usage: "research" },
];

#[pyfunction]
fn get_metric_semantics(metric_name: &str) -> PyResult<MetricSemantics> {
    METRIC_ROWS
        .iter()
        .find(|row| row.metric_name == metric_name)
        .cloned()
        .ok_or_else(|| PyKeyError::new_err(format!("unknown metric semantics: {metric_name}")))
}

#[pyfunction]
fn iter_metric_semantics() -> Vec<MetricSemantics> {
    let mut rows = METRIC_ROWS.to_vec();
    rows.sort_by(|left, right| left.metric_name.cmp(right.metric_name));
    rows
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<MetricSemantics>()?;
    module.add_function(wrap_pyfunction!(get_metric_semantics, module)?)?;
    module.add_function(wrap_pyfunction!(iter_metric_semantics, module)?)?;
    Ok(())
}
