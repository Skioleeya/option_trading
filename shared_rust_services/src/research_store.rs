use crate::research_pending_labels::{
    pending_key, recover_latest_feature_day, PendingOutcome,
};
use crate::research_store_support::{
    cleanup_tier_path, direction_to_code, ensure_dirs, et_date, gex_intensity_to_code, is_rth,
    iv_regime_to_code, l0_rust, parse_ts_any, parse_ts_text, project_allowed, settings_value,
    tier_schema, utc_iso, VALID_FORMATS, VALID_INTERVALS, VALID_VIEWS,
};
use crate::tactical::compute_vrp_impl;
use crate::research_store_io::{load_latest, load_range};
use chrono::{DateTime, Utc};
use chrono_tz::US::Eastern;
use pyo3::{exceptions::PyValueError, prelude::*, types::{PyDict, PyList, PyModule}};
use std::{collections::HashMap, fs, path::PathBuf};
use uuid::Uuid;
#[derive(Clone)]
struct ExportJob {
    status: String, path: String, format: String, error: Option<String>,
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
    last_persist_second: Option<i64>,
    rth_ticks_seen: u64,
    rth_rows_persisted: u64,
    non_rth_ticks_skipped: u64,
    write_failures: u64,
    last_persist_et: Option<String>,
}
#[pymethods]
impl ResearchFeatureStore {
    #[new]
    #[pyo3(signature = (*, root_dir=None, raw_retention_days=None, feature_retention_days=None, label_retention_days=None))]
    fn new(py: Python<'_>, root_dir: Option<String>, raw_retention_days: Option<i64>, feature_retention_days: Option<i64>, label_retention_days: Option<i64>) -> PyResult<Self> {
        let requested_root = PathBuf::from(root_dir.clone().unwrap_or(settings_value(py, "research_store_root", String::from("tmp/research_store"))?));
        let (raw_dir, feature_dir, label_dir, export_dir) =
            ensure_dirs(&requested_root).map_err(|err| PyValueError::new_err(err.to_string()))?;
        let recovery = recover_latest_feature_day(py, &feature_dir, &label_dir)?;
        let store = Self {
            root: requested_root,
            raw_dir,
            feature_dir,
            label_dir,
            export_dir,
            raw_retention_days: raw_retention_days.unwrap_or(settings_value(py, "research_raw_retention_days", 2_i64)?),
            feature_retention_days: feature_retention_days.unwrap_or(settings_value(py, "research_feature_retention_days", 20_i64)?),
            label_retention_days: label_retention_days.unwrap_or(settings_value(py, "research_label_retention_days", 20_i64)?),
            max_fields_per_query: settings_value(py, "history_max_fields_per_query", 64_usize)?,
            max_points_per_query: settings_value(py, "history_max_points_per_query", 1024_usize)?,
            pending_labels: recovery.pending_labels,
            jobs: HashMap::new(),
            last_cleanup_date: None,
            last_persist_second: None,
            rth_ticks_seen: 0,
            rth_rows_persisted: 0,
            non_rth_ticks_skipped: 0,
            write_failures: 0,
            last_persist_et: None,
        };
        if !recovery.recovered_rows.is_empty() {
            let replay_date = recovery
                .replay_date
                .ok_or_else(|| PyValueError::new_err("feature replay date missing for recovered label rows"))?;
            let rows = PyList::new(py, recovery.recovered_rows.iter())?;
            store.append_rows(py, &store.label_dir, "label", &replay_date, &rows)?;
        }
        Ok(store)
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
        if !is_rth(ts) {
            self.non_rth_ticks_skipped = self.non_rth_ticks_skipped.saturating_add(1);
            return Ok(());
        }
        self.rth_ticks_seen = self.rth_ticks_seen.saturating_add(1);
        let second_bucket = ts.timestamp();
        if self.last_persist_second == Some(second_bucket) { return Ok(()); }
        let decision = decision.bind(py);
        let aggregates = snapshot.getattr("aggregates")?;
        let micro = snapshot.getattr("microstructure")?;
        let native = l0_rust(py)?;
        let atm_iv = get_float(&aggregates, "atm_iv").unwrap_or(0.0);
        let direction = decision.getattr("direction")?.extract::<String>()?;
        let iv_regime = decision.getattr("iv_regime")?.extract::<String>()?;
        let gex_intensity = decision.getattr("gex_intensity")?.extract::<String>()?;
        let raw_row = PyDict::new(py);
        raw_row.set_item("data_timestamp", utc_iso(ts))?;
        raw_row.set_item("as_of_utc", &as_of_utc)?;
        raw_row.set_item("l0_version", l0_version)?;
        raw_row.set_item("symbol", "SPY")?;
        raw_row.set_item("spot", spot)?;
        for key_name in ["atm_iv","net_gex","call_wall","put_wall","flip_level"] {
            raw_row.set_item(key_name, get_float(&aggregates, key_name).unwrap_or(0.0))?;
        }
        raw_row.set_item("bbo_imbalance_raw", get_float(&micro, "bbo_imbalance_raw").unwrap_or(0.0))?;
        raw_row.set_item("session_phase", micro.getattr("session_phase").ok().and_then(|v| v.extract::<String>().ok()).unwrap_or_default())?;
        raw_row.set_item("stored_at", utc_iso(Utc::now()))?;

        let feature = PyDict::new(py);
        feature.set_item("data_timestamp", utc_iso(ts))?;
        feature.set_item("as_of_utc", &as_of_utc)?;
        feature.set_item("l0_version", l0_version)?;
        feature.set_item("symbol", "SPY")?;
        feature.set_item("spot", spot)?;
        feature.set_item("atm_iv", atm_iv)?;
        feature.set_item("net_gex", get_float(&aggregates, "net_gex").unwrap_or(0.0))?;
        feature.set_item("call_wall", get_float(&aggregates, "call_wall").unwrap_or(0.0))?;
        feature.set_item("put_wall", get_float(&aggregates, "put_wall").unwrap_or(0.0))?;
        feature.set_item("flip_level", get_float(&aggregates, "flip_level").unwrap_or(0.0))?;
        feature.set_item("bbo_imbalance_raw", get_float(&micro, "bbo_imbalance_raw").unwrap_or(0.0))?;
        feature.set_item(
            "session_phase",
            micro
                .getattr("session_phase")
                .ok()
                .and_then(|v| v.extract::<String>().ok())
                .unwrap_or_default(),
        )?;
        feature.set_item("stored_at", utc_iso(Utc::now()))?;
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
        let mm_flow = payload.getattr("fused_signal").ok().and_then(|v| v.downcast_into::<PyDict>().ok()).and_then(|d| d.get_item("mm_flow").ok().flatten()).and_then(|v| v.downcast_into::<PyDict>().ok()).ok_or_else(|| PyValueError::new_err("payload.fused_signal.mm_flow missing or invalid"))?;
        for key_name in [
            "net_delta_exposure_live", "net_gamma_exposure_live", "residual_delta_after_netting",
            "oi_participation_ratio_live", "flow_suppression_bias", "flow_dominance_ratio",
            "midpoint_tickrule_count", "condition_filtered_count", "complex_spread_count",
        ] { feature.set_item(key_name, required_finite_f64(&mm_flow, key_name, "payload.fused_signal.mm_flow")?)?; }
        let diagnostics_any = snapshot
            .getattr("extra_metadata")?
            .downcast_into::<PyDict>()
            .ok()
            .and_then(|d| d.get_item("longport_option_diagnostics").ok().flatten())
            .unwrap_or_else(|| PyDict::new(py).into_any());
        let longport_cols = native.call_method1("service_research_longport_columns", (diagnostics_any,))?.downcast_into::<PyDict>()?;
        let official_hv_decimal = longport_cols.get_item("longport_official_hv_decimal").ok().flatten().and_then(|v| v.extract::<f64>().ok());
        feature.set_item("longport_official_hv_decimal", official_hv_decimal)?;
        feature.set_item("longport_official_hv_sample_count", longport_cols.get_item("longport_official_hv_sample_count").ok().flatten().and_then(|v| v.extract::<i64>().ok()).unwrap_or(0))?;
        feature.set_item("longport_official_hv_age_sec", longport_cols.get_item("longport_official_hv_age_sec").ok().flatten().and_then(|v| v.extract::<f64>().ok()))?;
        if let Some(hv) = official_hv_decimal.filter(|hv| *hv > 0.0 && atm_iv > 0.0) {
            feature.set_item("vrp_official_hv_based", compute_vrp_impl(Some(atm_iv), Some(hv)))?;
        } else {
            feature.set_item("vrp_official_hv_based", py.None())?;
        }
        feature.set_item("direction_code", direction_to_code(&direction))?;
        feature.set_item("iv_regime_code", iv_regime_to_code(&iv_regime))?;
        feature.set_item("gex_intensity_code", gex_intensity_to_code(&gex_intensity))?;
        feature.set_item("confidence", decision.getattr("confidence").ok().and_then(|v| v.extract::<f64>().ok()).unwrap_or(0.0))?;
        feature.set_item("max_impact", decision.getattr("max_impact").ok().and_then(|v| v.extract::<f64>().ok()).unwrap_or(0.0))?;
        feature.set_item("dealer_squeeze_alert", micro.getattr("dealer_squeeze_alert").ok().and_then(|v| v.extract::<bool>().ok()).unwrap_or(false))?;

        if let Err(err) = self.append_rows(py, &self.raw_dir, "raw", &store_date, &PyList::new(py, [raw_row])?) {
            self.write_failures = self.write_failures.saturating_add(1);
            return Err(err);
        }
        if let Err(err) = self.append_rows(py, &self.feature_dir, "feature", &store_date, &PyList::new(py, [feature])?) {
            self.write_failures = self.write_failures.saturating_add(1);
            return Err(err);
        }
        self.last_persist_second = Some(second_bucket);
        self.rth_rows_persisted = self.rth_rows_persisted.saturating_add(1);
        self.last_persist_et = Some(ts.with_timezone(&Eastern).to_rfc3339());
        self.update_pending_labels(py, ts, spot)?;
        let key = pending_key(ts, l0_version, "SPY");
        self.pending_labels
            .entry(key)
            .or_insert_with(|| PendingOutcome::new(ts, l0_version, "SPY".into(), spot));
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
        out.set_item("rth_ticks_seen", self.rth_ticks_seen)?;
        out.set_item("rth_rows_persisted", self.rth_rows_persisted)?;
        out.set_item("non_rth_ticks_skipped", self.non_rth_ticks_skipped)?;
        out.set_item("write_failures", self.write_failures)?;
        out.set_item("last_persist_et", self.last_persist_et.clone())?;
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
            state.advance(ts, spot);
            let elapsed = state.elapsed_seconds(ts);
            if state.matured(ts) {
                rows.push(native.call_method1("service_research_label_row", (utc_iso(state.ts), state.l0_version, state.symbol.clone(), utc_iso(Utc::now()), state.label_value("1m"), state.label_value("5m"), state.label_value("15m"), state.label_value("60m"), state.min_ret, safe_std(&state.log_returns), elapsed))?.unbind());
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
fn required_finite_f64(dict: &Bound<'_, PyDict>, key: &str, ctx: &str) -> PyResult<f64> {
    let raw = dict.get_item(key).ok().flatten().ok_or_else(|| PyValueError::new_err(format!("{ctx} missing key: {key}")))?;
    let value = raw.extract::<f64>().map_err(|_| PyValueError::new_err(format!("{ctx} key not float: {key}")))?;
    if !value.is_finite() { return Err(PyValueError::new_err(format!("{ctx} key not finite: {key}"))); }
    Ok(value)
}
fn path_obj(py: Python<'_>, path: &PathBuf) -> PyResult<Py<PyAny>> { Ok(py.import("pathlib")?.getattr("Path")?.call1((path.to_string_lossy().to_string(),))?.unbind()) }
fn safe_std(values: &[f64]) -> f64 { if values.len() < 2 { 0.0 } else { let mean = values.iter().sum::<f64>() / values.len() as f64; let var = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (values.len() as f64 - 1.0); var.max(0.0).sqrt() } }
fn get_float(obj: &Bound<'_, PyAny>, key: &str) -> Option<f64> { obj.getattr(key).ok().and_then(|v| v.extract::<f64>().ok()).filter(|v| v.is_finite()) }
fn job_dict(py: Python<'_>, job: &ExportJob) -> Py<PyDict> { let d = PyDict::new(py); let _ = d.set_item("status",&job.status); let _ = d.set_item("path",&job.path); let _ = d.set_item("format",&job.format); if let Some(error)=&job.error { let _ = d.set_item("error",error); } d.unbind() }
fn err_dict(py: Python<'_>, message: &str) -> PyResult<Py<PyDict>> { let d = PyDict::new(py); d.set_item("error", message)?; Ok(d.unbind()) }
pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ResearchFeatureStore>()?;
    m.add_function(wrap_pyfunction!(cleanup_tier, m)?)?;
    Ok(())
}
