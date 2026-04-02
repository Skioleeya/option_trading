use chrono::{DateTime, Utc};
use chrono_tz::US::Eastern;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyModule};
use std::collections::{HashMap, VecDeque};

fn parse_ts_text(text: &str) -> Option<DateTime<Utc>> {
    let normalized = if text.ends_with('Z') {
        format!("{}+00:00", &text[..text.len() - 1])
    } else {
        text.to_string()
    };
    DateTime::parse_from_rfc3339(&normalized).ok().map(|dt| dt.with_timezone(&Utc))
}

fn parse_ts(raw: &Bound<'_, PyAny>) -> PyResult<Option<DateTime<Utc>>> {
    if raw.is_none() {
        return Ok(None);
    }
    if let Ok(text) = raw.extract::<String>() {
        let normalized = if text.ends_with('Z') {
            format!("{}+00:00", &text[..text.len() - 1])
        } else {
            text
        };
        if let Ok(dt) = DateTime::parse_from_rfc3339(&normalized) {
            return Ok(Some(dt.with_timezone(&Utc)));
        }
        return Ok(None);
    }
    let py = raw.py();
    let datetime = py.import("datetime")?.getattr("datetime")?;
    if raw.is_instance(&datetime)? {
        let timezone = py.import("datetime")?.getattr("timezone")?.getattr("utc")?;
        let utc_dt = raw.call_method1("astimezone", (timezone,))?;
        let iso = utc_dt.call_method0("isoformat")?.extract::<String>()?;
        return Ok(parse_ts_text(&iso));
    }
    Ok(None)
}

fn to_positive(raw: &Bound<'_, PyAny>) -> Option<f64> {
    raw.extract::<f64>().ok().filter(|value| value.is_finite() && *value > 0.0)
}

fn settings_float(py: Python<'_>, name: &str, default: f64) -> PyResult<f64> {
    let settings = py.import("shared.config")?.getattr("settings")?;
    Ok(settings.getattr(name)?.extract::<f64>().unwrap_or(default))
}

fn empty_relation(py: Python<'_>) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("window_seconds", 120)?;
    out.set_item("iv_change_pp", py.None())?;
    out.set_item("price_change_pct", py.None())?;
    out.set_item("beta_pp_per_pct", py.None())?;
    out.set_item("state", "UNAVAILABLE")?;
    Ok(out.unbind())
}

#[pyclass(module = "shared_rust.services", unsendable)]
pub struct HeaderVolatilityContextService {
    research_store: Py<PyAny>,
    lookback_days: usize,
    relation_window_seconds: f64,
    min_history_days: usize,
    history_cache_ttl_seconds: f64,
    history_fetch_count: usize,
    relation_history: VecDeque<(f64, f64, f64)>,
    history_cache_trade_date: Option<String>,
    history_cache_until_mono: f64,
    history_cache_values: Vec<f64>,
}

#[pymethods]
impl HeaderVolatilityContextService {
    #[new]
    #[pyo3(signature = (*, research_store, lookback_days=20, relation_window_seconds=120.0, min_history_days=5, history_cache_ttl_seconds=60.0, history_fetch_count=512))]
    fn new(
        research_store: Py<PyAny>,
        lookback_days: usize,
        relation_window_seconds: f64,
        min_history_days: usize,
        history_cache_ttl_seconds: f64,
        history_fetch_count: usize,
    ) -> Self {
        Self {
            research_store,
            lookback_days,
            relation_window_seconds,
            min_history_days,
            history_cache_ttl_seconds,
            history_fetch_count,
            relation_history: VecDeque::with_capacity(512),
            history_cache_trade_date: None,
            history_cache_until_mono: 0.0,
            history_cache_values: Vec::new(),
        }
    }

    #[pyo3(signature = (*, snapshot, spot, atm_iv))]
    fn build(&mut self, py: Python<'_>, snapshot: Py<PyAny>, spot: f64, atm_iv: f64) -> PyResult<Py<PyDict>> {
        let time_mod = py.import("time")?;
        let now_mono = time_mod.getattr("monotonic")?.call0()?.extract::<f64>()?;
        let snapshot = snapshot.bind(py);
        let current_trade_date = self.current_trade_date(snapshot)?;
        self.record_relation_point(now_mono, spot, atm_iv);
        let closes = self.load_completed_day_closes(py, &current_trade_date, now_mono)?;
        let aux = self.extract_aux(snapshot)?;
        let l0_rust = py.import("shared.services.l0_runtime.native_loader")?.getattr("l0_rust")?;

        let out = PyDict::new(py);
        out.set_item("lookback_days", self.lookback_days)?;
        out.set_item("lookback_effective_days", closes.len())?;
        let iv_kwargs = PyDict::new(py);
        iv_kwargs.set_item("closes", PyList::new(py, &closes)?)?;
        iv_kwargs.set_item("min_history_days", self.min_history_days)?;
        out.set_item("ivr", l0_rust.call_method("service_header_compute_ivr", (atm_iv,), Some(&iv_kwargs))?)?;
        out.set_item("ivp", l0_rust.call_method("service_header_compute_ivp", (atm_iv,), Some(&iv_kwargs))?)?;
        let term = PyDict::new(py);
        term.set_item("primary", self.term_primary(py, &l0_rust, atm_iv, &aux)?)?;
        term.set_item("secondary", self.term_secondary(py, &l0_rust, atm_iv, &aux)?)?;
        out.set_item("term_structure", term)?;
        out.set_item("iv_price_relation", self.iv_price_relation(py)?)?;
        Ok(out.unbind())
    }
}

impl HeaderVolatilityContextService {
    fn record_relation_point(&mut self, now_mono: f64, spot: f64, atm_iv: f64) {
        if spot.is_finite() && spot > 0.0 && atm_iv.is_finite() && atm_iv > 0.0 {
            self.relation_history.push_back((now_mono, spot, atm_iv));
        }
        let cutoff = now_mono - self.relation_window_seconds;
        while self
            .relation_history
            .front()
            .is_some_and(|(ts, _, _)| *ts < cutoff)
        {
            let _ = self.relation_history.pop_front();
        }
    }

    fn current_trade_date(&self, snapshot: &Bound<'_, PyAny>) -> PyResult<String> {
        let extra = snapshot.getattr("extra_metadata").ok().and_then(|value| value.downcast_into::<PyDict>().ok());
        let source_ts = extra.as_ref().and_then(|dict| dict.get_item("source_data_timestamp_utc").ok().flatten());
        let computed = snapshot.getattr("computed_at").ok();
        let parsed = if let Some(raw) = source_ts {
            parse_ts(&raw)?
        } else if let Some(raw) = computed {
            parse_ts(&raw)?
        } else {
            None
        };
        Ok(parsed.unwrap_or_else(Utc::now).with_timezone(&Eastern).format("%Y-%m-%d").to_string())
    }

    fn extract_aux(&self, snapshot: &Bound<'_, PyAny>) -> PyResult<HashMap<String, Py<PyAny>>> {
        let mut out = HashMap::new();
        if let Ok(extra) = snapshot.getattr("extra_metadata") {
            if let Ok(extra_dict) = extra.downcast::<PyDict>() {
                if let Ok(Some(aux)) = extra_dict.get_item("header_volatility_aux") {
                    if let Ok(aux_dict) = aux.downcast::<PyDict>() {
                        for (key, value) in aux_dict.iter() {
                            out.insert(key.extract::<String>()?, value.unbind());
                        }
                    }
                }
            }
        }
        Ok(out)
    }

    fn load_completed_day_closes(
        &mut self,
        py: Python<'_>,
        current_trade_date: &str,
        now_mono: f64,
    ) -> PyResult<Vec<f64>> {
        if self.history_cache_trade_date.as_deref() == Some(current_trade_date)
            && now_mono < self.history_cache_until_mono
        {
            return Ok(self.history_cache_values.clone());
        }
        let kwargs = PyDict::new(py);
        kwargs.set_item("count", self.history_fetch_count)?;
        kwargs.set_item("view", "feature")?;
        kwargs.set_item("fields", PyList::new(py, ["data_timestamp", "atm_iv"])?)?;
        let rows_any = self
            .research_store
            .bind(py)
            .call_method("latest_feature_view", (), Some(&kwargs))?;
        let rows = rows_any.downcast::<PyList>().map_err(|_| PyValueError::new_err("latest_feature_view must return list"))?;
        let mut per_day: HashMap<String, (DateTime<Utc>, f64)> = HashMap::new();
        for row in rows.iter() {
            let dict = match row.downcast::<PyDict>() {
                Ok(value) => value,
                Err(_) => continue,
            };
            let Some(raw_ts) = dict.get_item("data_timestamp").ok().flatten() else {
                continue;
            };
            let Some(timestamp) = parse_ts(&raw_ts)? else {
                continue;
            };
            let trade_date = timestamp.with_timezone(&Eastern).format("%Y-%m-%d").to_string();
            if trade_date == current_trade_date {
                continue;
            }
            let Some(iv_raw) = dict
                .get_item("atm_iv")
                .ok()
                .flatten()
                .and_then(|raw| to_positive(&raw)) else {
                continue;
            };
            match per_day.get(&trade_date) {
                Some((prev_ts, _)) if *prev_ts >= timestamp => {}
                _ => {
                    per_day.insert(trade_date, (timestamp, iv_raw));
                }
            }
        }
        let mut values: Vec<(String, DateTime<Utc>, f64)> = per_day
            .into_iter()
            .map(|(trade_date, (timestamp, value))| (trade_date, timestamp, value))
            .collect();
        values.sort_by(|a, b| a.0.cmp(&b.0).then(a.1.cmp(&b.1)));
        let closes: Vec<f64> = values.into_iter().map(|(_, _, value)| value).rev().take(self.lookback_days).collect::<Vec<_>>().into_iter().rev().collect();
        self.history_cache_trade_date = Some(current_trade_date.to_string());
        self.history_cache_until_mono = now_mono + self.history_cache_ttl_seconds;
        self.history_cache_values = closes.clone();
        Ok(closes)
    }

    fn term_primary(&self, py: Python<'_>, l0_rust: &Bound<'_, PyAny>, atm_iv: f64, aux: &HashMap<String, Py<PyAny>>) -> PyResult<Py<PyDict>> {
        let anchor_iv = aux.get("atm_iv_1dte").and_then(|value| to_positive(value.bind(py)));
        let ratio = l0_rust.call_method1("service_header_safe_ratio", (atm_iv, anchor_iv))?;
        let state = l0_rust.call_method1("service_header_term_state", (ratio.clone(),))?;
        let out = PyDict::new(py);
        out.set_item("anchor", "1DTE")?;
        out.set_item("symbol", "SPY.US")?;
        out.set_item("expiry", aux.get("next_expiry").map(|value| value.clone_ref(py)).unwrap_or_else(|| py.None()))?;
        out.set_item("iv", anchor_iv)?;
        out.set_item("ratio", ratio)?;
        out.set_item("state", state)?;
        Ok(out.unbind())
    }

    fn term_secondary(&self, py: Python<'_>, l0_rust: &Bound<'_, PyAny>, atm_iv: f64, aux: &HashMap<String, Py<PyAny>>) -> PyResult<Py<PyDict>> {
        let vix_iv = aux.get("vix_iv_decimal").and_then(|value| to_positive(value.bind(py)));
        let ratio = l0_rust.call_method1("service_header_safe_ratio", (atm_iv, vix_iv))?;
        let state = l0_rust.call_method1("service_header_term_state", (ratio.clone(),))?;
        let out = PyDict::new(py);
        out.set_item("anchor", ".VIX.US")?;
        out.set_item("symbol", ".VIX.US")?;
        out.set_item("iv_decimal", vix_iv)?;
        out.set_item("ratio", ratio)?;
        out.set_item("state", state)?;
        Ok(out.unbind())
    }

    fn iv_price_relation(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        if self.relation_history.len() < 2 {
            return empty_relation(py);
        }
        let oldest = self.relation_history.front().copied().unwrap();
        let newest = self.relation_history.back().copied().unwrap();
        if oldest.1 <= 0.0 {
            return empty_relation(py);
        }
        let price_change_pct = ((newest.1 - oldest.1) / oldest.1) * 100.0;
        let iv_change_pp = (newest.2 - oldest.2) * 100.0;
        let spot_threshold = settings_float(py, "spot_roc_threshold_pct", 0.0)?;
        let iv_threshold = settings_float(py, "iv_roc_threshold_pct", 0.0)?;
        let price_sig = price_change_pct.abs() >= spot_threshold.max(0.0);
        let iv_sig = iv_change_pp.abs() >= iv_threshold.max(0.0);
        let state = if price_sig && iv_sig {
            if price_change_pct.signum() == iv_change_pp.signum() {
                "POSITIVE_DIVERGENCE"
            } else {
                "INVERSE_CONFIRM"
            }
        } else if iv_sig {
            "VOL_LEAD"
        } else if price_sig {
            "PRICE_LEAD"
        } else {
            "UNAVAILABLE"
        };
        let out = PyDict::new(py);
        out.set_item("window_seconds", self.relation_window_seconds as i64)?;
        out.set_item("iv_change_pp", iv_change_pp)?;
        out.set_item("price_change_pct", price_change_pct)?;
        if price_change_pct.abs() >= 1e-9 {
            out.set_item("beta_pp_per_pct", iv_change_pp / price_change_pct.abs())?;
        } else {
            out.set_item("beta_pp_per_pct", py.None())?;
        }
        out.set_item("state", state)?;
        Ok(out.unbind())
    }
}

pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<HeaderVolatilityContextService>()?;
    Ok(())
}
