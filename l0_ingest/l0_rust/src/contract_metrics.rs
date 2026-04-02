use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyModule};

#[derive(Clone, Copy)]
struct MetricRow {
    metric_name: &'static str,
    classification: &'static str,
    unit: &'static str,
    sign_convention: &'static str,
    data_prerequisites: &'static str,
    canonical_description: &'static str,
    live_usage: &'static str,
}

const METRIC_ROWS: [MetricRow; 14] = [
    MetricRow {
        metric_name: "net_gex",
        classification: "proxy",
        unit: "MMUSD",
        sign_convention: "positive = call gross proxy minus put gross proxy",
        data_prerequisites: "public option chain with gamma, OI, multiplier, spot",
        canonical_description: "OI-based net GEX structural proxy; not dealer inventory truth.",
        live_usage: "live",
    },
    MetricRow {
        metric_name: "zero_gamma_level",
        classification: "proxy",
        unit: "underlying price",
        sign_convention: "spot level where OI-based net GEX proxy crosses zero",
        data_prerequisites: "same prerequisites as net_gex plus spot-grid recomputation",
        canonical_description: "OI-based zero-gamma proxy derived from spot-grid recomputation.",
        live_usage: "live",
    },
    MetricRow {
        metric_name: "call_wall",
        classification: "proxy",
        unit: "underlying price",
        sign_convention: "strike with peak call-side GEX proxy",
        data_prerequisites: "per-strike call-side GEX proxy",
        canonical_description: "Trading-practice resistance proxy; not a unified academic wall definition.",
        live_usage: "live",
    },
    MetricRow {
        metric_name: "put_wall",
        classification: "proxy",
        unit: "underlying price",
        sign_convention: "strike with peak put-side GEX proxy",
        data_prerequisites: "per-strike put-side GEX proxy",
        canonical_description: "Trading-practice support proxy; not a unified academic wall definition.",
        live_usage: "live",
    },
    MetricRow {
        metric_name: "flip_level_cumulative",
        classification: "proxy",
        unit: "underlying price",
        sign_convention: "first strike where cumulative net GEX proxy crosses zero",
        data_prerequisites: "sorted per-strike cumulative net GEX proxy profile",
        canonical_description: "Trading-practice cumulative flip proxy; distinct from zero-gamma recomputation.",
        live_usage: "live",
    },
    MetricRow {
        metric_name: "FLOW_D",
        classification: "heuristic",
        unit: "signed flow score input",
        sign_convention: "positive = bullish call-side pressure proxy, negative = bearish put-side pressure proxy",
        data_prerequisites: "public volume, gamma proxy, spot",
        canonical_description: "Research heuristic combining public volume and gamma proxy; not a unified academic exact formula.",
        live_usage: "live",
    },
    MetricRow {
        metric_name: "FLOW_E",
        classification: "heuristic",
        unit: "signed flow score input",
        sign_convention: "sign follows IV premium/discount direction by option type",
        data_prerequisites: "public volume, vanna proxy, IV, HV",
        canonical_description: "Research heuristic combining vanna proxy and IV premium spread; not a unified academic exact formula.",
        live_usage: "live",
    },
    MetricRow {
        metric_name: "FLOW_G",
        classification: "heuristic",
        unit: "signed flow score input",
        sign_convention: "positive = call-side OI expansion proxy, negative = put-side OI expansion proxy",
        data_prerequisites: "public OI delta, IV, ATM IV, turnover",
        canonical_description: "Public-data proxy for OI momentum; not a unified academic exact formula.",
        live_usage: "live",
    },
    MetricRow {
        metric_name: "vol_risk_premium",
        classification: "proxy",
        unit: "% points",
        sign_convention: "ATM_IV(%) - baseline_HV(%)",
        data_prerequisites: "ATM IV and configured baseline HV",
        canonical_description: "Live proxy VRP based on configured baseline HV, not canonical realized-vol VRP.",
        live_usage: "live",
    },
    MetricRow {
        metric_name: "guard_vrp_proxy_pct",
        classification: "heuristic",
        unit: "% points",
        sign_convention: "ATM_IV(%) - realized_vol_proxy(%) derived from |vol_accel_ratio|",
        data_prerequisites: "ATM IV and vol_accel_ratio",
        canonical_description: "Guard-only VRP proxy used for veto hysteresis; not shared with live feature VRP.",
        live_usage: "live",
    },
    MetricRow {
        metric_name: "skew_25d_normalized",
        classification: "proxy",
        unit: "normalized skew ratio",
        sign_convention: "(put_iv - call_iv) / atm_iv using nearest ±25d legs",
        data_prerequisites: "ATM IV plus nearest ±25d legs",
        canonical_description: "Legacy normalized skew field retained for compatibility and research export.",
        live_usage: "legacy-only",
    },
    MetricRow {
        metric_name: "rr25_call_minus_put",
        classification: "proxy",
        unit: "IV points",
        sign_convention: "call_iv(+25d) - put_iv(-25d)",
        data_prerequisites: "nearest ±25d legs and valid delta gating",
        canonical_description: "Canonical 25d risk reversal used as the live skew source of truth.",
        live_usage: "live",
    },
    MetricRow {
        metric_name: "net_charm_raw_sum",
        classification: "proxy",
        unit: "raw Greek sum",
        sign_convention: "sum of per-contract charm sensitivities",
        data_prerequisites: "per-contract charm values across the chain",
        canonical_description: "Canonical raw chain sum of charm sensitivities; not position-weighted exposure.",
        live_usage: "live",
    },
    MetricRow {
        metric_name: "net_vanna_raw_sum",
        classification: "proxy",
        unit: "raw Greek sum",
        sign_convention: "sum of per-contract vanna sensitivities",
        data_prerequisites: "per-contract vanna values across the chain",
        canonical_description: "Canonical raw chain sum of vanna sensitivities; not position-weighted exposure.",
        live_usage: "research",
    },
];

fn build_metric_row<'py>(py: Python<'py>, row: MetricRow) -> PyResult<Bound<'py, PyDict>> {
    let out = PyDict::new(py);
    out.set_item("metric_name", row.metric_name)?;
    out.set_item("classification", row.classification)?;
    out.set_item("unit", row.unit)?;
    out.set_item("sign_convention", row.sign_convention)?;
    out.set_item("data_prerequisites", row.data_prerequisites)?;
    out.set_item("canonical_description", row.canonical_description)?;
    out.set_item("live_usage", row.live_usage)?;
    Ok(out)
}

#[pyfunction]
fn metric_semantics_rows(py: Python<'_>) -> PyResult<Py<PyList>> {
    let rows = PyList::empty(py);
    for row in METRIC_ROWS {
        rows.append(build_metric_row(py, row)?)?;
    }
    Ok(rows.unbind())
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(metric_semantics_rows, module)?)?;
    Ok(())
}
