use crate::research_store_support::{
    cleanup_tier_path, ensure_dirs, et_date, l0_rust, parse_ts_any, parse_ts_text, project_allowed,
    settings_value, tier_schema, utc_iso, VALID_FORMATS, VALID_INTERVALS, VALID_VIEWS,
};
use chrono::{DateTime, Utc};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyModule};
use std::env;
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use uuid::Uuid;

#[derive(Clone, Default)]
struct PendingOutcome {
    ts: DateTime<Utc>,
    l0_version: i64,
    symbol: String,
    base_spot: f64,
    last_spot: f64,
    min_ret: f64,
    log_returns: Vec<f64>,
    fwd_ret: HashMap<&'static str, Option<f64>>,
}

#[derive(Clone)]
struct ExportJob {
    status: String,
    path: String,
    format: String,
    error: Option<String>,
}

fn horizons() -> HashMap<&'static str, Option<f64>> {
    HashMap::from([("1m", None), ("5m", None), ("15m", None), ("60m", None)])
}

#[pyclass(module = "shared_rust.services", unsendable)]
pub struct ResearchFeatureStore {
    root: PathBuf,
    raw_dir: PathBuf,
    feature_dir: PathBuf,
    label_dir: PathBuf,
    export_dir: PathBuf,
    raw_retention_days: i64,
    feature_retention_days: i64,
    label_retention_days: i64,
    max_fields_per_query: usize,
    max_points_per_query: usize,
    pending_labels: HashMap<String, PendingOutcome>,
    jobs: HashMap<String, ExportJob>,
    last_cleanup_date: Option<String>,
    last_sample_bucket_5s: Option<i64>,
    last_direction: Option<String>,
    last_net_gex: Option<f64>,
}

#[pymethods]
impl ResearchFeatureStore {
    #[new]
    #[pyo3(signature = (*, root_dir=None, raw_retention_days=None, feature_retention_days=None, label_retention_days=None))]
    fn new(py: Python<'_>, root_dir: Option<String>, raw_retention_days: Option<i64>, feature_retention_days: Option<i64>, label_retention_days: Option<i64>) -> PyResult<Self> {
        let requested_root = PathBuf::from(root_dir.clone().unwrap_or(settings_value(py, "research_store_root", String::from("tmp/research_store"))?));
        let (root, raw_dir, feature_dir, label_dir, export_dir) = match ensure_dirs(&requested_root) {
            Ok((raw_dir, feature_dir, label_dir, export_dir)) => (requested_root, raw_dir, feature_dir, label_dir, export_dir),
            Err(_) if root_dir.is_none() => {
                let fallback_root = env::temp_dir().join("option_v3_research_store");
                let (raw_dir, feature_dir, label_dir, export_dir) =
                    ensure_dirs(&fallback_root).map_err(|err| PyValueError::new_err(err.to_string()))?;
                (fallback_root, raw_dir, feature_dir, label_dir, export_dir)
            }
            Err(err) => return Err(PyValueError::new_err(err.to_string())),
        };
        Ok(Self {
            root,
            raw_dir,
            feature_dir,
            label_dir,
            export_dir,
            raw_retention_days: raw_retention_days.unwrap_or(settings_value(py, "research_raw_retention_days", 2_i64)?),
            feature_retention_days: feature_retention_days.unwrap_or(settings_value(py, "research_feature_retention_days", 20_i64)?),
            label_retention_days: label_retention_days.unwrap_or(settings_value(py, "research_label_retention_days", 20_i64)?),
            max_fields_per_query: settings_value(py, "history_max_fields_per_query", 64_usize)?,
            max_points_per_query: settings_value(py, "history_max_points_per_query", 1024_usize)?,
            pending_labels: HashMap::new(),
            jobs: HashMap::new(),
            last_cleanup_date: None,
            last_sample_bucket_5s: None,
            last_direction: None,
            last_net_gex: None,
        })
    }

    #[getter(_raw_dir)]
    fn raw_dir(&self, py: Python<'_>) -> PyResult<Py<PyAny>> { path_obj(py, &self.raw_dir) }
    #[getter(_feature_dir)]
    fn feature_dir(&self, py: Python<'_>) -> PyResult<Py<PyAny>> { path_obj(py, &self.feature_dir) }
    #[getter(_label_dir)]
    fn label_dir(&self, py: Python<'_>) -> PyResult<Py<PyAny>> { path_obj(py, &self.label_dir) }
    #[getter(_export_dir)]
    fn export_dir(&self, py: Python<'_>) -> PyResult<Py<PyAny>> { path_obj(py, &self.export_dir) }
    #[getter(_max_points_per_query)]
    fn max_points(&self) -> usize { self.max_points_per_query }
    #[setter(_max_points_per_query)]
    fn set_max_points(&mut self, value: usize) { self.max_points_per_query = value; }
    #[getter(_max_fields_per_query)]
    fn max_fields(&self) -> usize { self.max_fields_per_query }

    #[pyo3(signature = (*, decision, snapshot, payload))]
    fn append_tick(&mut self, py: Python<'_>, decision: Py<PyAny>, snapshot: Py<PyAny>, payload: Py<PyAny>) -> PyResult<()> {
        let snapshot = snapshot.bind(py);
        let payload = payload.bind(py);
        let ts = payload.getattr("data_timestamp").ok().and_then(|raw| parse_ts_any(&raw).ok().flatten()).unwrap_or_else(Utc::now);
        let spot = get_float(snapshot, "spot").or_else(|| payload.getattr("spot").ok().and_then(|raw| raw.extract::<f64>().ok())).unwrap_or(0.0);
        if !(spot.is_finite() && spot > 0.0) { return Ok(()); }
        let l0_version = snapshot.getattr("version").ok().and_then(|v| v.extract::<i64>().ok()).unwrap_or(0);
        let as_of_utc = payload.getattr("data_timestamp").ok().and_then(|raw| raw.extract::<String>().ok()).unwrap_or_else(|| utc_iso(ts));
        let store_date = et_date(ts);
        self.cleanup_retention_if_needed(py, &store_date)?;
        self.update_pending_labels(py, ts, spot)?;
        let key = format!("{}|{}|SPY", ts.to_rfc3339(), l0_version);
        self.pending_labels.entry(key).or_insert_with(|| PendingOutcome { ts, l0_version, symbol: "SPY".into(), base_spot: spot, last_spot: spot, min_ret: 0.0, log_returns: Vec::new(), fwd_ret: horizons() });

        let native = l0_rust(py)?;
        let decision = decision.bind(py);
        let aggregates = snapshot.getattr("aggregates")?;
        let micro = snapshot.getattr("microstructure")?;
        let net_gex = get_float(&aggregates, "net_gex").unwrap_or(0.0);
        let guard_actions = decision.getattr("guard_actions").ok().unwrap_or(PyList::empty(py).into_any());
        let emit_state = native.call_method(
            "service_research_emit_decision",
            (ts.timestamp() as f64, decision.getattr("direction")?.extract::<String>()?, guard_actions.len().unwrap_or(0), net_gex),
            Some(&dict_args(py, &[("last_direction", opt_py_str(py, self.last_direction.as_deref())), ("last_net_gex", opt_py_float(py, self.last_net_gex)), ("last_bucket_5s", opt_py_i64(py, self.last_sample_bucket_5s))])?),
        )?.downcast_into::<PyDict>()?;
        if emit_state.get_item("sampled_5s")?.and_then(|v| v.extract::<bool>().ok()).unwrap_or(false) {
            self.last_sample_bucket_5s = emit_state.get_item("bucket_5s")?.and_then(|v| v.extract::<i64>().ok());
        }
        self.last_direction = Some(decision.getattr("direction")?.extract::<String>()?);
        self.last_net_gex = Some(net_gex);
        if !emit_state.get_item("emit")?.and_then(|v| v.extract::<bool>().ok()).unwrap_or(false) { return Ok(()); }

        let mut raw_row = PyDict::new(py);
        raw_row.set_item("data_timestamp", utc_iso(ts))?;
        raw_row.set_item("as_of_utc", as_of_utc)?;
        raw_row.set_item("l0_version", l0_version)?;
        raw_row.set_item("symbol", "SPY")?;
        raw_row.set_item("spot", spot)?;
        for key_name in ["atm_iv","net_gex","net_vanna_raw_sum","net_charm_raw_sum","call_wall","put_wall","flip_level"] {
            raw_row.set_item(key_name, get_float(&aggregates, key_name).unwrap_or(0.0))?;
        }
        raw_row.set_item("net_vanna", get_float(&aggregates, "net_vanna_raw_sum").unwrap_or(0.0))?;
        raw_row.set_item("net_charm", get_float(&aggregates, "net_charm_raw_sum").unwrap_or(0.0))?;
        for key_name in ["vpin_1m","vpin_5m","vpin_15m","vpin_composite","bbo_imbalance_raw","bbo_ewma_fast","bbo_ewma_slow","bbo_persistence","vol_accel_ratio","vol_accel_threshold","vol_entropy"] {
            raw_row.set_item(key_name, get_float(&micro, key_name).unwrap_or(0.0))?;
        }
        raw_row.set_item("vol_accel_elevated", micro.getattr("vol_accel_elevated").ok().and_then(|v| v.extract::<bool>().ok()).unwrap_or(false))?;
        raw_row.set_item("session_phase", micro.getattr("session_phase").ok().and_then(|v| v.extract::<String>().ok()).unwrap_or_default())?;
        raw_row.set_item("mtf_consensus", "NEUTRAL")?;
        raw_row.set_item("mtf_alignment", 0.0)?;
        raw_row.set_item("mtf_strength", 0.0)?;
        raw_row.set_item("stored_at", utc_iso(Utc::now()))?;
        let feature = PyDict::new(py);
        for (key, value) in raw_row.iter() { feature.set_item(key, value)?; }
        let feature_vector = decision.getattr("feature_vector").ok().and_then(|v| v.downcast_into::<PyDict>().ok());
        for key_name in ["skew_25d_normalized","rr25_call_minus_put","realized_volatility_15m","vol_risk_premium","vrp_realized_based"] {
            let value = feature_vector
                .as_ref()
                .and_then(|d| d.get_item(key_name).ok().flatten())
                .and_then(|v| v.extract::<f64>().ok());
            match value {
                Some(number) => feature.set_item(key_name, number)?,
                None => feature.set_item(key_name, py.None())?,
            }
        }
        let diagnostics = snapshot
            .getattr("extra_metadata")?
            .downcast_into::<PyDict>()
            .ok()
            .and_then(|d| d.get_item("longport_option_diagnostics").ok().flatten())
            .unwrap_or_else(|| PyDict::new(py).into_any());
        for (key, value) in native.call_method1("service_research_longport_columns", (diagnostics,))?.downcast_into::<PyDict>()?.iter() {
            feature.set_item(key, value)?;
        }
        let official_hv_decimal = feature
            .get_item("longport_official_hv_decimal")
            .ok()
            .flatten()
            .and_then(|v| v.extract::<f64>().ok());
        let atm_iv = get_float(&aggregates, "atm_iv").unwrap_or(0.0);
        if let Some(hv) = official_hv_decimal.filter(|hv| *hv > 0.0 && atm_iv > 0.0) {
            let vrp = py
                .import("shared.system.tactical_triad_logic")?
                .getattr("compute_vrp")?
                .call1((atm_iv, hv))?;
            feature.set_item("vrp_official_hv_based", vrp)?;
        } else {
            feature.set_item("vrp_official_hv_based", py.None())?;
        }
        feature.set_item("direction", decision.getattr("direction")?)?;
        feature.set_item("confidence", decision.getattr("confidence").ok().and_then(|v| v.extract::<f64>().ok()).unwrap_or(0.0))?;
        feature.set_item("pre_guard_direction", decision.getattr("pre_guard_direction").ok().and_then(|v| v.extract::<String>().ok()).unwrap_or_else(|| "NEUTRAL".into()))?;
        feature.set_item("guard_actions_json", py.import("json")?.call_method1("dumps", (guard_actions,))?)?;
        for key_name in ["fusion_weights","signal_summary","feature_vector"] {
            feature.set_item(format!("{key_name}_json"), py.import("json")?.call_method1("dumps", (decision.getattr(key_name).ok().unwrap_or(PyDict::new(py).into_any()),))?)?;
        }
        feature.set_item("iv_regime", decision.getattr("iv_regime").ok().and_then(|v| v.extract::<String>().ok()).unwrap_or_else(|| "NORMAL".into()))?;
        feature.set_item("gex_intensity", decision.getattr("gex_intensity").ok().and_then(|v| v.extract::<String>().ok()).unwrap_or_else(|| "NEUTRAL".into()))?;
        feature.set_item("max_impact", decision.getattr("max_impact").ok().and_then(|v| v.extract::<f64>().ok()).unwrap_or(0.0))?;
        feature.set_item("dealer_squeeze_alert", micro.getattr("dealer_squeeze_alert").ok().and_then(|v| v.extract::<bool>().ok()).unwrap_or(false))?;
        self.append_rows(py, &self.raw_dir, "raw", &store_date, &PyList::new(py, [raw_row])?)?;
        self.append_rows(py, &self.feature_dir, "feature", &store_date, &PyList::new(py, [feature])?)?;
        Ok(())
    }

    #[pyo3(signature = (*, start, end, view="feature", fields=None, interval="1s", fmt="jsonl"))]
    fn query(&mut self, py: Python<'_>, start: &str, end: &str, view: &str, fields: Option<Vec<String>>, interval: &str, fmt: &str) -> PyResult<Py<PyDict>> {
        if !VALID_VIEWS.contains(&view) || view == "audit" { return err_dict(py, "invalid view"); }
        if !VALID_FORMATS.contains(&fmt) { return err_dict(py, "invalid format"); }
        if !VALID_INTERVALS.iter().any(|(name, _)| *name == interval) { return err_dict(py, "invalid interval"); }
        let Some(start_dt) = parse_ts_text(start) else { return err_dict(py, "invalid start/end timestamp"); };
        let Some(end_dt) = parse_ts_text(end) else { return err_dict(py, "invalid start/end timestamp"); };
        if end_dt < start_dt { return err_dict(py, "end must be >= start"); }
        let mut records = match self.query_records(py, start_dt, end_dt, view, fields.clone(), interval) {
            Ok(value) => value,
            Err(err) => return err_dict(py, &err.to_string()),
        };
        if records.len() > self.max_points_per_query {
            let job_id = self.enqueue_export(py, &records, fmt)?;
            let out = PyDict::new(py);
            out.set_item("status", "accepted")?;
            out.set_item("job_id", job_id)?;
            out.set_item("count", records.len())?;
            out.set_item("message", "Query exceeds inline limit; async export started.")?;
            return Ok(out.unbind());
        }
        let out = PyDict::new(py);
        out.set_item("status", "ok")?;
        out.set_item("count", records.len())?;
        out.set_item("format", fmt)?;
        if fmt == "parquet" {
            let native = l0_rust(py)?;
            let rows = PyList::new(py, records.iter())?;
            out.set_item("content_type", "application/x-parquet")?;
            out.set_item("bytes", native.call_method1("service_research_records_to_parquet", (rows,))?)?;
        } else {
            out.set_item("records", PyList::new(py, records.drain(..))?)?;
        }
        Ok(out.unbind())
    }

    fn get_export_job(&self, py: Python<'_>, job_id: &str) -> PyResult<Option<Py<PyDict>>> { Ok(self.jobs.get(job_id).map(|job| job_dict(py, job))) }
    fn read_export(&self, _py: Python<'_>, job_id: &str) -> PyResult<Option<(String, Vec<u8>)>> {
        let Some(job) = self.jobs.get(job_id) else { return Ok(None) };
        if job.status != "done" { return Ok(None); }
        let bytes = fs::read(&job.path).map_err(|err| PyValueError::new_err(err.to_string()))?;
        let content_type = if job.path.ends_with(".parquet") { "application/x-parquet" } else { "application/x-ndjson" };
        Ok(Some((content_type.to_string(), bytes)))
    }

    #[pyo3(signature = (*, count, view, fields=None))]
    fn latest_feature_view(&self, py: Python<'_>, count: usize, view: &str, fields: Option<Vec<String>>) -> PyResult<Vec<Py<PyAny>>> {
        let mut records = self.load_latest_feature(py, count.max(256))?;
        if view == "compact" { records = self.to_compact(py, records)?; }
        if let Some(field_list) = fields { records = self.project_fields(py, records, view, field_list)?; }
        Ok(if count > 0 && records.len() > count { records.split_off(records.len() - count) } else { records })
    }

    fn diagnostics(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let out = PyDict::new(py);
        out.set_item("root", self.root.to_string_lossy().to_string())?;
        out.set_item("pending_labels", self.pending_labels.len())?;
        out.set_item("export_jobs", self.jobs.len())?;
        out.set_item("raw_retention_days", self.raw_retention_days)?;
        out.set_item("feature_retention_days", self.feature_retention_days)?;
        out.set_item("label_retention_days", self.label_retention_days)?;
        Ok(out.unbind())
    }
}

impl ResearchFeatureStore {
    fn enqueue_export(&mut self, py: Python<'_>, records: &[Py<PyAny>], fmt: &str) -> PyResult<String> {
        let job_id = Uuid::new_v4().simple().to_string();
        let path = self.export_dir.join(format!("{job_id}.{}", if fmt == "parquet" { "parquet" } else { "jsonl" }));
        let native = l0_rust(py)?;
        let data: Vec<u8> = if fmt == "parquet" {
            native.call_method1("service_research_records_to_parquet", (PyList::new(py, records.iter())?,))?.extract()?
        } else {
            native.call_method1("service_research_jsonl_bytes", (PyList::new(py, records.iter())?,))?.extract()?
        };
        fs::write(&path, data).map_err(|err| PyValueError::new_err(err.to_string()))?;
        self.jobs.insert(job_id.clone(), ExportJob { status: "done".into(), path: path.to_string_lossy().to_string(), format: fmt.into(), error: None });
        Ok(job_id)
    }

    fn query_records(&self, py: Python<'_>, start_dt: DateTime<Utc>, end_dt: DateTime<Utc>, view: &str, fields: Option<Vec<String>>, interval: &str) -> PyResult<Vec<Py<PyAny>>> {
        let mut records = self.load_feature_range(py, start_dt, end_dt)?;
        if view == "compact" { records = self.to_compact(py, records)?; } else { self.attach_labels(py, &mut records, start_dt, end_dt)?; }
        if let Some(field_list) = fields { records = self.project_fields(py, records, view, field_list)?; }
        self.apply_interval(py, records, interval)
    }

    fn load_feature_range(&self, py: Python<'_>, start_dt: DateTime<Utc>, end_dt: DateTime<Utc>) -> PyResult<Vec<Py<PyAny>>> { load_range(py, &self.feature_dir, "feature", start_dt, end_dt) }
    fn load_label_range(&self, py: Python<'_>, start_dt: DateTime<Utc>, end_dt: DateTime<Utc>) -> PyResult<Vec<Py<PyAny>>> { load_range(py, &self.label_dir, "label", start_dt, end_dt) }
    fn load_latest_feature(&self, py: Python<'_>, count: usize) -> PyResult<Vec<Py<PyAny>>> { load_latest(py, &self.feature_dir, "feature", count) }

    fn to_compact(&self, py: Python<'_>, records: Vec<Py<PyAny>>) -> PyResult<Vec<Py<PyAny>>> {
        let native = l0_rust(py)?;
        records.into_iter().map(|row| Ok(native.call_method1("service_research_to_compact_record", (row.bind(py),))?.unbind())).collect()
    }

    fn project_fields(&self, py: Python<'_>, records: Vec<Py<PyAny>>, view: &str, fields: Vec<String>) -> PyResult<Vec<Py<PyAny>>> {
        if fields.len() > self.max_fields_per_query { return Err(PyValueError::new_err("too many fields requested")); }
        let native = l0_rust(py)?;
        let projected = native.call_method1("service_research_project_records", (PyList::new(py, records.iter())?, fields, project_allowed(view), self.max_fields_per_query))?;
        Ok(projected.downcast::<PyList>()?.iter().map(|row| row.unbind()).collect())
    }

    fn apply_interval(&self, py: Python<'_>, records: Vec<Py<PyAny>>, interval: &str) -> PyResult<Vec<Py<PyAny>>> {
        let step = VALID_INTERVALS.iter().find(|(name, _)| *name == interval).map(|(_, step)| *step).unwrap_or(1);
        if step <= 1 { return Ok(records); }
        let native = l0_rust(py)?;
        let reduced = native.call_method1("service_research_apply_interval", (PyList::new(py, records.iter())?, step))?;
        Ok(reduced.downcast::<PyList>()?.iter().map(|row| row.unbind()).collect())
    }

    fn attach_labels(&self, py: Python<'_>, records: &mut [Py<PyAny>], start_dt: DateTime<Utc>, end_dt: DateTime<Utc>) -> PyResult<()> {
        let labels = self.load_label_range(py, start_dt, end_dt)?;
        let mut by_key: HashMap<(String, i64), Py<PyAny>> = HashMap::new();
        for row in labels { let dict = row.bind(py).downcast::<PyDict>()?; by_key.insert((dict.get_item("data_timestamp")?.unwrap().extract()?, dict.get_item("l0_version")?.unwrap().extract()?), row.clone_ref(py)); }
        for row in records.iter_mut() {
            let dict = row.bind(py).downcast::<PyDict>()?;
            let key = (dict.get_item("data_timestamp")?.unwrap().extract::<String>()?, dict.get_item("l0_version")?.unwrap().extract::<i64>()?);
            if let Some(label) = by_key.get(&key) {
                let label_dict = label.bind(py).downcast::<PyDict>()?;
                for (k, v) in label_dict.iter() { dict.set_item(k, v)?; }
            }
        }
        Ok(())
    }

    fn append_rows(&self, py: Python<'_>, dir: &PathBuf, tier: &str, date_str: &str, rows: &Bound<'_, PyList>) -> PyResult<()> {
        let path = dir.join(format!("{tier}_{date_str}.parquet"));
        l0_rust(py)?.call_method1("service_research_append_parquet_rows", (path.to_string_lossy().to_string(), rows, tier_schema(py, tier)?))?;
        Ok(())
    }

    fn cleanup_retention_if_needed(&mut self, py: Python<'_>, date_str: &str) -> PyResult<()> {
        if self.last_cleanup_date.as_deref() == Some(date_str) { return Ok(()); }
        self.last_cleanup_date = Some(date_str.to_string());
        let now_et = parse_date(date_str)?;
        cleanup_tier_path(&self.raw_dir, "raw", now_et, self.raw_retention_days)?;
        cleanup_tier_path(&self.feature_dir, "feature", now_et, self.feature_retention_days)?;
        cleanup_tier_path(&self.label_dir, "label", now_et, self.label_retention_days)?;
        let _ = py;
        Ok(())
    }

    fn update_pending_labels(&mut self, py: Python<'_>, ts: DateTime<Utc>, spot: f64) -> PyResult<()> {
        let native = l0_rust(py)?;
        let mut done = Vec::new();
        let mut rows = Vec::new();
        for (key, state) in self.pending_labels.iter_mut() {
            let elapsed = (ts - state.ts).num_seconds().max(0) as f64;
            let current_ret = (spot / state.base_spot) - 1.0;
            state.min_ret = state.min_ret.min(current_ret);
            if state.last_spot > 0.0 && spot > 0.0 { state.log_returns.push((spot / state.last_spot).ln()); }
            state.last_spot = spot;
            for (horizon, sec) in [("1m", 60.0), ("5m", 300.0), ("15m", 900.0), ("60m", 3600.0)] {
                if state.fwd_ret[horizon].is_none() && elapsed >= sec { state.fwd_ret.insert(horizon, Some(current_ret)); }
            }
            if elapsed >= 3600.0 {
                rows.push(native.call_method1("service_research_label_row", (utc_iso(state.ts), state.l0_version, state.symbol.clone(), utc_iso(Utc::now()), state.fwd_ret["1m"], state.fwd_ret["5m"], state.fwd_ret["15m"], state.fwd_ret["60m"], state.min_ret, safe_std(&state.log_returns), elapsed))?.unbind());
                done.push(key.clone());
            }
        }
        for key in done { self.pending_labels.remove(&key); }
        if !rows.is_empty() { self.append_rows(py, &self.label_dir, "label", &et_date(ts), &PyList::new(py, rows.iter())?)?; }
        Ok(())
    }
}

#[pyfunction]
fn cleanup_tier(py: Python<'_>, tier_dir: &str, prefix: &str, now_et_date: &str, retention_days: i64) -> PyResult<()> {
    let _ = py;
    cleanup_tier_path(&PathBuf::from(tier_dir), prefix, parse_date(now_et_date)?, retention_days)
}

fn parse_date(text: &str) -> PyResult<chrono::NaiveDate> {
    chrono::NaiveDate::parse_from_str(text, "%Y%m%d")
        .or_else(|_| chrono::NaiveDate::parse_from_str(text, "%Y-%m-%d"))
        .map_err(|err| PyValueError::new_err(err.to_string()))
}

fn path_obj(py: Python<'_>, path: &PathBuf) -> PyResult<Py<PyAny>> { Ok(py.import("pathlib")?.getattr("Path")?.call1((path.to_string_lossy().to_string(),))?.unbind()) }
fn safe_std(values: &[f64]) -> f64 { if values.len() < 2 { 0.0 } else { let mean = values.iter().sum::<f64>() / values.len() as f64; let var = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (values.len() as f64 - 1.0); var.max(0.0).sqrt() } }
fn get_float(obj: &Bound<'_, PyAny>, key: &str) -> Option<f64> { obj.getattr(key).ok().and_then(|v| v.extract::<f64>().ok()).filter(|v| v.is_finite()) }
fn opt_py_str<'py>(py: Python<'py>, value: Option<&str>) -> Bound<'py, PyAny> { value.unwrap_or("").into_pyobject(py).unwrap().into_any() }
fn opt_py_float<'py>(py: Python<'py>, value: Option<f64>) -> Bound<'py, PyAny> { value.map_or(py.None().bind(py).clone(), |v| v.into_pyobject(py).unwrap().into_any()) }
fn opt_py_i64<'py>(py: Python<'py>, value: Option<i64>) -> Bound<'py, PyAny> { value.map_or(py.None().bind(py).clone(), |v| v.into_pyobject(py).unwrap().into_any()) }
fn dict_args<'py>(py: Python<'py>, items: &[(&str, Bound<'py, PyAny>)]) -> PyResult<Bound<'py, PyDict>> { let d = PyDict::new(py); for (k,v) in items { d.set_item(*k, v)?; } Ok(d) }
fn job_dict(py: Python<'_>, job: &ExportJob) -> Py<PyDict> { let d = PyDict::new(py); let _ = d.set_item("status",&job.status); let _ = d.set_item("path",&job.path); let _ = d.set_item("format",&job.format); if let Some(error)=&job.error { let _ = d.set_item("error",error); } d.unbind() }
fn err_dict(py: Python<'_>, message: &str) -> PyResult<Py<PyDict>> { let d = PyDict::new(py); d.set_item("error", message)?; Ok(d.unbind()) }

fn load_range(py: Python<'_>, tier_dir: &PathBuf, prefix: &str, start_dt: DateTime<Utc>, end_dt: DateTime<Utc>) -> PyResult<Vec<Py<PyAny>>> {
    let native = l0_rust(py)?;
    let names: Vec<String> = fs::read_dir(tier_dir).map_err(|err| PyValueError::new_err(err.to_string()))?.filter_map(Result::ok).filter_map(|e| e.file_name().into_string().ok()).collect();
    let files = native.call_method1("service_research_range_files", (names, prefix, et_date(start_dt), et_date(end_dt)))?.downcast_into::<PyList>()?;
    let mut rows = Vec::new();
    for file in files.iter() {
        let path = tier_dir.join(file.extract::<String>()?);
        let out = native.call_method1("service_research_read_parquet_rows", (path.to_string_lossy().to_string(),))?;
        for row in out.downcast::<PyList>()?.iter() {
            let dict = row.downcast::<PyDict>()?;
            if let Some(ts) = dict.get_item("data_timestamp")?.and_then(|v| parse_ts_any(&v).ok().flatten()) {
                if ts >= start_dt && ts <= end_dt { rows.push(row.unbind()); }
            }
        }
    }
    Ok(rows)
}

fn load_latest(py: Python<'_>, tier_dir: &PathBuf, prefix: &str, count: usize) -> PyResult<Vec<Py<PyAny>>> {
    let native = l0_rust(py)?;
    let names: Vec<String> = fs::read_dir(tier_dir).map_err(|err| PyValueError::new_err(err.to_string()))?.filter_map(Result::ok).filter_map(|e| e.file_name().into_string().ok()).collect();
    let files = native.call_method1("service_research_latest_files", (names, prefix))?.downcast_into::<PyList>()?;
    let mut rows = Vec::new();
    for file in files.iter() {
        let path = tier_dir.join(file.extract::<String>()?);
        let out = native.call_method1("service_research_read_parquet_rows", (path.to_string_lossy().to_string(),))?;
        for row in out.downcast::<PyList>()?.iter() { rows.push(row.unbind()); }
        if rows.len() >= count { break; }
    }
    rows.sort_by_key(|row| row.bind(py).downcast::<PyDict>().ok().and_then(|dict| dict.get_item("data_timestamp").ok().flatten()).and_then(|v| v.extract::<String>().ok()).unwrap_or_default());
    Ok(rows)
}

pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ResearchFeatureStore>()?;
    m.add_function(wrap_pyfunction!(cleanup_tier, m)?)?;
    Ok(())
}
