use super::common::{
    as_list, get_attr_bool, get_attr_f64, get_attr_string, logger, make_flow_component,
    make_flow_output, settings_value, FLOW_INTENSITY_VALUES,
};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyModule};

#[pyclass(module = "shared_rust.services", unsendable)]
pub struct FlowEngineD;

#[pymethods]
impl FlowEngineD {
    #[new]
    fn new() -> Self {
        Self
    }

    fn compute(&self, py: Python<'_>, inputs: &Bound<'_, PyAny>) -> PyResult<Vec<Py<PyAny>>> {
        let mut results = Vec::new();
        for input in as_list(inputs)?.iter() {
            let volume = get_attr_f64(&input, "volume");
            let gamma = get_attr_f64(&input, "gamma");
            let spot = get_attr_f64(&input, "spot");
            let symbol = get_attr_string(&input, "symbol", "SPY");
            let strike = get_attr_f64(&input, "strike");
            let option_type = get_attr_string(&input, "option_type", "CALL");
            if volume <= 0.0 || gamma <= 0.0 || spot <= 0.0 {
                results.push(make_flow_component(
                    py,
                    &symbol,
                    strike,
                    &option_type,
                    0.0,
                    false,
                    "zero volume/gamma/spot",
                )?);
                continue;
            }
            let sign = if option_type == "PUT" { -1.0 } else { 1.0 };
            let flow = volume * gamma * spot.powi(2) * 100.0 * 0.01 * sign;
            results.push(make_flow_component(py, &symbol, strike, &option_type, flow, true, "")?);
        }
        Ok(results)
    }
}

#[pyclass(module = "shared_rust.services", unsendable)]
pub struct FlowEngineE;

#[pymethods]
impl FlowEngineE {
    #[new]
    fn new() -> Self {
        Self
    }

    fn compute(&self, py: Python<'_>, inputs: &Bound<'_, PyAny>) -> PyResult<Vec<Py<PyAny>>> {
        let mut results = Vec::new();
        for input in as_list(inputs)?.iter() {
            let volume = get_attr_f64(&input, "volume");
            let symbol = get_attr_string(&input, "symbol", "SPY");
            let strike = get_attr_f64(&input, "strike");
            let option_type = get_attr_string(&input, "option_type", "CALL");
            if volume <= 0.0 {
                results.push(make_flow_component(py, &symbol, strike, &option_type, 0.0, false, "zero volume")?);
                continue;
            }
            let iv = get_attr_f64(&input, "implied_volatility");
            let hv = get_attr_f64(&input, "historical_volatility");
            if iv == 0.0 && hv == 0.0 {
                results.push(make_flow_component(py, &symbol, strike, &option_type, 0.0, true, "IV=HV=0, no signal")?);
                continue;
            }
            let delta_iv = iv - hv;
            let vanna = get_attr_f64(&input, "vanna").abs();
            let type_sign = if option_type == "PUT" { -1.0 } else { 1.0 };
            let iv_sign = if delta_iv >= 0.0 { 1.0 } else { -1.0 };
            let flow = volume * 100.0 * vanna * delta_iv.abs() * type_sign * iv_sign;
            results.push(make_flow_component(py, &symbol, strike, &option_type, flow, true, "")?);
        }
        Ok(results)
    }
}

#[pyclass(module = "shared_rust.services", unsendable)]
pub struct FlowEngineG;

#[pymethods]
impl FlowEngineG {
    #[new]
    fn new() -> Self {
        Self
    }

    #[pyo3(signature = (inputs, redis=None, oi_store=None, date_str=None))]
    fn compute(
        &self,
        py: Python<'_>,
        inputs: &Bound<'_, PyAny>,
        redis: Option<&Bound<'_, PyAny>>,
        oi_store: Option<&Bound<'_, PyAny>>,
        date_str: Option<String>,
    ) -> PyResult<Vec<Py<PyAny>>> {
        let mut results = Vec::new();
        if redis.is_none() {
            logger(py)?.call_method1(
                "warning",
                ("[FlowEngineG] Redis unavailable - returning zero flows (graceful degradation)",),
            )?;
            for input in as_list(inputs)?.iter() {
                results.push(make_flow_component(
                    py,
                    &get_attr_string(&input, "symbol", "SPY"),
                    get_attr_f64(&input, "strike"),
                    &get_attr_string(&input, "option_type", "CALL"),
                    0.0,
                    false,
                    "redis_unavailable",
                )?);
            }
            return Ok(results);
        }

        let get_oi_delta = py.import("shared.cache.oi_snapshot")?.getattr("get_oi_delta")?;
        for input in as_list(inputs)?.iter() {
            let symbol = get_attr_string(&input, "symbol", "SPY");
            let strike = get_attr_f64(&input, "strike");
            let option_type = get_attr_string(&input, "option_type", "CALL");
            let volume = get_attr_f64(&input, "volume");
            let turnover = get_attr_f64(&input, "turnover");
            if volume <= 0.0 || turnover <= 0.0 {
                results.push(make_flow_component(
                    py,
                    &symbol,
                    strike,
                    &option_type,
                    0.0,
                    false,
                    "zero volume/turnover",
                )?);
                continue;
            }

            let delta_kwargs = PyDict::new(py);
            if let Some(ref value) = date_str {
                delta_kwargs.set_item("date_str", value)?;
            }
            let mut delta_oi = get_oi_delta
                .call(
                    (redis, symbol.clone(), get_attr_f64(&input, "open_interest")),
                    Some(&delta_kwargs),
                )?
                .extract::<f64>()
                .unwrap_or(0.0);
            if delta_oi == 0.0 {
                if let Some(store) = oi_store {
                    if let Ok(baseline) = store.call_method1("get_baseline", (date_str.clone().unwrap_or_default(),)) {
                        if let Ok(baseline) = baseline.downcast::<PyDict>() {
                            delta_oi = baseline
                                .get_item(&symbol)?
                                .and_then(|value| value.extract::<f64>().ok())
                                .map(|value| get_attr_f64(&input, "open_interest") - value)
                                .unwrap_or(0.0);
                        }
                    }
                }
            }
            if delta_oi == 0.0 {
                results.push(make_flow_component(py, &symbol, strike, &option_type, 0.0, true, "no_oi_history")?);
                continue;
            }
            let atm_iv = get_attr_f64(&input, "atm_iv");
            let iv_norm = if atm_iv > 0.0 {
                get_attr_f64(&input, "implied_volatility") / atm_iv
            } else {
                1.0
            };
            let type_sign = if option_type == "PUT" { -1.0 } else { 1.0 };
            let flow = delta_oi * iv_norm * turnover * type_sign;
            results.push(make_flow_component(py, &symbol, strike, &option_type, flow, true, "")?);
        }
        Ok(results)
    }
}

#[pyclass(module = "shared_rust.services", unsendable)]
pub struct InstitutionalSweepDetector;

#[pymethods]
impl InstitutionalSweepDetector {
    #[new]
    fn new() -> Self {
        Self
    }

    fn detect(&self, py: Python<'_>, symbols: Vec<String>, z_scores: Vec<f64>) -> PyResult<Py<PyAny>> {
        let result = PyDict::new(py);
        for symbol in &symbols {
            result.set_item(symbol, false)?;
        }
        if symbols.len() < 3 {
            return Ok(result.unbind().into_any());
        }

        let active: Vec<bool> = z_scores.iter().map(|score| score.abs() > 1.5).collect();
        for index in 0..symbols.len() {
            if !active[index] {
                continue;
            }
            let start = index.saturating_sub(2);
            let end = (index + 3).min(symbols.len());
            let neighbors = (start..end)
                .filter(|other| *other != index && active[*other])
                .count();
            if neighbors < 2 {
                continue;
            }
            result.set_item(&symbols[index], true)?;
            for other in start..end {
                if other != index && active[other] {
                    result.set_item(&symbols[other], true)?;
                }
            }
        }
        Ok(result.unbind().into_any())
    }
}

#[pyclass(module = "shared_rust.services", unsendable)]
pub struct DEGComposer {
    detector: InstitutionalSweepDetector,
}

#[pymethods]
impl DEGComposer {
    #[new]
    fn new() -> Self {
        Self {
            detector: InstitutionalSweepDetector,
        }
    }

    #[pyo3(signature = (d_results, e_results, g_results, inputs_by_symbol, gex_regime, is_charm_surge=false, ttm_seconds=None))]
    fn compose(
        &self,
        py: Python<'_>,
        d_results: &Bound<'_, PyAny>,
        e_results: &Bound<'_, PyAny>,
        g_results: &Bound<'_, PyAny>,
        inputs_by_symbol: &Bound<'_, PyDict>,
        gex_regime: String,
        is_charm_surge: bool,
        ttm_seconds: Option<f64>,
    ) -> PyResult<Vec<Py<PyAny>>> {
        let index = |items: &Bound<'_, PyAny>| -> PyResult<std::collections::HashMap<String, f64>> {
            let mut map = std::collections::HashMap::new();
            for item in as_list(items)?.iter() {
                if get_attr_bool(&item, "is_valid", true) {
                    map.insert(get_attr_string(&item, "symbol", "SPY"), get_attr_f64(&item, "flow_value"));
                }
            }
            Ok(map)
        };
        let map_d = index(d_results)?;
        let map_e = index(e_results)?;
        let map_g = index(g_results)?;
        let g_active = as_list(g_results)?
            .iter()
            .any(|item| get_attr_bool(&item, "is_valid", true));

        let mut symbols: Vec<String> = map_d
            .keys()
            .chain(map_e.keys())
            .chain(map_g.keys())
            .cloned()
            .collect();
        symbols.sort();
        symbols.dedup();
        if symbols.is_empty() {
            return Ok(Vec::new());
        }

        let z_score = |values: &[f64]| -> Vec<f64> {
            let mean = values.iter().sum::<f64>() / values.len() as f64;
            let variance = values.iter().map(|value| (value - mean).powi(2)).sum::<f64>() / values.len() as f64;
            let std = variance.max(0.0).sqrt();
            if std < 1e-9 {
                vec![0.0; values.len()]
            } else {
                values.iter().map(|value| (value - mean) / std).collect()
            }
        };
        let vals_d: Vec<f64> = symbols.iter().map(|key| *map_d.get(key).unwrap_or(&0.0)).collect();
        let vals_e: Vec<f64> = symbols.iter().map(|key| *map_e.get(key).unwrap_or(&0.0)).collect();
        let vals_g: Vec<f64> = symbols.iter().map(|key| *map_g.get(key).unwrap_or(&0.0)).collect();
        let z_d = z_score(&vals_d);
        let z_e = z_score(&vals_e);
        let z_g = z_score(&vals_g);

        let (mut w_d, mut w_e, mut w_g) = if gex_regime == "ACCELERATION" || is_charm_surge {
            (
                settings_value(py, "flow_charm_surge_weight_d", 0.4_f64)?,
                settings_value(py, "flow_charm_surge_weight_e", 0.3_f64)?,
                settings_value(py, "flow_charm_surge_weight_g", 0.3_f64)?,
            )
        } else {
            (
                settings_value(py, "flow_neutral_gex_weight_d", 0.4_f64)?,
                settings_value(py, "flow_neutral_gex_weight_e", 0.3_f64)?,
                settings_value(py, "flow_neutral_gex_weight_g", 0.3_f64)?,
            )
        };
        if !g_active {
            let total = (w_d + w_e).max(1e-9);
            w_d /= total;
            w_e /= total;
            w_g = 0.0;
        }

        let initial: Vec<f64> = (0..symbols.len())
            .map(|index| (w_d * z_d[index]) + (w_e * z_e[index]) + (w_g * z_g[index]))
            .collect();
        let sweep_binding = self.detector.detect(py, symbols.clone(), initial.clone())?;
        let sweep_map = sweep_binding.bind(py).downcast::<PyDict>()?;

        let tau = ttm_seconds.unwrap_or(23_400.0) / 23_400.0;
        let time_factor = (-tau).exp();
        let sweep_multiplier = settings_value(py, "flow_sweep_multiplier", 1.25_f64)?;
        let market_depth = settings_value(py, "flow_market_depth_baseline", 1.0_f64)?;
        let extreme_threshold = settings_value(py, "flow_zscore_extreme_threshold", 2.0_f64)?;
        let high_threshold = settings_value(py, "flow_intensity_high_threshold", 1.0_f64)?;
        let mut outputs = Vec::new();

        for (index, symbol) in symbols.iter().enumerate() {
            let Some(input_row) = inputs_by_symbol.get_item(symbol)? else {
                continue;
            };
            let mut deg = initial[index];
            let is_sweep = if let Some(value) = sweep_map.get_item(symbol)? {
                value.extract::<bool>().unwrap_or(false)
            } else {
                false
            };
            if is_sweep {
                deg *= sweep_multiplier;
            }
            let abs_flow_total =
                map_d.get(symbol).copied().unwrap_or(0.0).abs()
                    + map_e.get(symbol).copied().unwrap_or(0.0).abs()
                    + map_g.get(symbol).copied().unwrap_or(0.0).abs();
            let impact_index =
                (abs_flow_total * get_attr_f64(&input_row, "gamma").abs() * time_factor)
                    / market_depth.max(1e-9);
            let direction = if deg > 0.1 {
                "BULLISH"
            } else if deg < -0.1 {
                "BEARISH"
            } else {
                "NEUTRAL"
            };
            let intensity = match deg.abs() {
                value if value >= extreme_threshold => FLOW_INTENSITY_VALUES[0],
                value if value >= high_threshold => FLOW_INTENSITY_VALUES[1],
                value if value >= 0.5 => FLOW_INTENSITY_VALUES[2],
                _ => FLOW_INTENSITY_VALUES[3],
            };
            let is_sweep_obj = is_sweep.into_pyobject(py)?.to_owned().into_any();
            let engine_d_active_obj = map_d.contains_key(symbol).into_pyobject(py)?.to_owned().into_any();
            let engine_e_active_obj = map_e.contains_key(symbol).into_pyobject(py)?.to_owned().into_any();
            let engine_g_active_obj = g_active.into_pyobject(py)?.to_owned().into_any();
            outputs.push(make_flow_output(
                py,
                &[
                    ("symbol", symbol.into_pyobject(py)?.into_any()),
                    ("option_type", get_attr_string(&input_row, "option_type", "CALL").into_pyobject(py)?.into_any()),
                    ("strike", get_attr_f64(&input_row, "strike").into_pyobject(py)?.into_any()),
                    ("implied_volatility", get_attr_f64(&input_row, "implied_volatility").into_pyobject(py)?.into_any()),
                    ("volume", get_attr_f64(&input_row, "volume").round().into_pyobject(py)?.into_any()),
                    ("turnover", get_attr_f64(&input_row, "turnover").into_pyobject(py)?.into_any()),
                    ("flow_d", map_d.get(symbol).copied().unwrap_or(0.0).into_pyobject(py)?.into_any()),
                    ("flow_e", map_e.get(symbol).copied().unwrap_or(0.0).into_pyobject(py)?.into_any()),
                    ("flow_g", map_g.get(symbol).copied().unwrap_or(0.0).into_pyobject(py)?.into_any()),
                    ("flow_d_z", z_d[index].into_pyobject(py)?.into_any()),
                    ("flow_e_z", z_e[index].into_pyobject(py)?.into_any()),
                    ("flow_g_z", z_g[index].into_pyobject(py)?.into_any()),
                    ("flow_deg", deg.into_pyobject(py)?.into_any()),
                    ("impact_index", impact_index.into_pyobject(py)?.into_any()),
                    ("is_sweep", is_sweep_obj),
                    ("flow_direction", direction.into_pyobject(py)?.into_any()),
                    ("flow_intensity", intensity.into_pyobject(py)?.into_any()),
                    ("engine_d_active", engine_d_active_obj),
                    ("engine_e_active", engine_e_active_obj),
                    ("engine_g_active", engine_g_active_obj),
                ],
            )?);
        }
        Ok(outputs)
    }
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<FlowEngineD>()?;
    module.add_class::<FlowEngineE>()?;
    module.add_class::<FlowEngineG>()?;
    module.add_class::<InstitutionalSweepDetector>()?;
    module.add_class::<DEGComposer>()?;
    Ok(())
}
