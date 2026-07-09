use crate::research_pending_labels::{pending_key, recover_latest_canonical_day, PendingOutcome};
use crate::research_store_build::parse_append_inputs;
use crate::research_store_support::{
    cleanup_tier_path, ensure_dirs, et_date, l0_rust, parse_ts_text, tier_schema, VALID_FORMATS,
    VALID_INTERVALS, VALID_VIEWS,
};
use pyo3::{
    exceptions::PyValueError,
    prelude::*,
    types::{PyDict, PyList, PyModule},
};
use std::{collections::HashMap, fs, path::PathBuf};
use uuid::Uuid;

#[derive(Clone)]
struct ExportJob {
    status: String,
    path: String,
    format: String,
    error: Option<String>,
}

#[pyclass(module = "shared_rust.services", unsendable)]
pub struct ResearchFeatureStore {
    pub(crate) root: PathBuf,
    pub(crate) canonical_dir: PathBuf,
    pub(crate) export_dir: PathBuf,
    pub(crate) canonical_retention_days: i64,
    pub(crate) max_fields_per_query: usize,
    pub(crate) max_points_per_query: usize,
    pub(crate) pending_labels: HashMap<String, PendingOutcome>,
    jobs: HashMap<String, ExportJob>,
    last_cleanup_date: Option<String>,
    last_persist_second: Option<i64>,
    rows_persisted_today: u64,
    non_rth_ticks_skipped: u64,
    write_failures: u64,
    last_persist_et: Option<String>,
}

#[pymethods]
impl ResearchFeatureStore {
    #[new]
    #[pyo3(signature = (*, root_dir=None, raw_retention_days=None, feature_retention_days=None, label_retention_days=None))]
    fn new(
        py: Python<'_>,
        root_dir: Option<String>,
        raw_retention_days: Option<i64>,
        feature_retention_days: Option<i64>,
        label_retention_days: Option<i64>,
    ) -> PyResult<Self> {
        let requested_root = PathBuf::from(root_dir.clone().unwrap_or(
            py.import("shared.config")?
                .getattr("settings")?
                .getattr("research_store_root")?
                .extract::<String>()?,
        ));
        let (canonical_dir, export_dir) =
            ensure_dirs(&requested_root).map_err(|err| PyValueError::new_err(err.to_string()))?;
        let retention_candidates = [
            raw_retention_days.unwrap_or(default_setting(py, "research_raw_retention_days", 2)?),
            feature_retention_days.unwrap_or(default_setting(py, "research_feature_retention_days", 20)?),
            label_retention_days.unwrap_or(default_setting(py, "research_label_retention_days", 20)?),
        ];
        let recovery = recover_latest_canonical_day(py, &canonical_dir)?;
        let mut store = Self {
            root: requested_root,
            canonical_dir,
            export_dir,
            canonical_retention_days: retention_candidates.into_iter().max().unwrap_or(1),
            max_fields_per_query: default_setting(py, "history_max_fields_per_query", 64)?,
            max_points_per_query: default_setting(py, "history_max_points_per_query", 1024)?,
            pending_labels: recovery.pending_labels,
            jobs: HashMap::new(),
            last_cleanup_date: recovery.replay_date.clone(),
            last_persist_second: None,
            rows_persisted_today: recovery.rows_persisted_today,
            non_rth_ticks_skipped: 0,
            write_failures: 0,
            last_persist_et: None,
        };
        if recovery.changed {
            let replay_date = recovery
                .replay_date
                .ok_or_else(|| PyValueError::new_err("canonical replay date missing for recovered labels"))?;
            store.persist_day_rows(py, &replay_date, &PyList::new(py, recovery.replay_rows.iter())?)?;
            store.rows_persisted_today = recovery.replay_rows.len() as u64;
        }
        Ok(store)
    }

    #[getter(_canonical_dir)]
    fn canonical_dir(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        path_obj(py, &self.canonical_dir)
    }

    #[getter(_export_dir)]
    fn export_dir(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        path_obj(py, &self.export_dir)
    }

    #[getter(_max_points_per_query)]
    fn max_points(&self) -> usize {
        self.max_points_per_query
    }

    #[setter(_max_points_per_query)]
    fn set_max_points(&mut self, value: usize) {
        self.max_points_per_query = value;
    }

    #[getter(_max_fields_per_query)]
    fn max_fields(&self) -> usize {
        self.max_fields_per_query
    }

    #[pyo3(signature = (*, decision, snapshot, payload))]
    fn append_tick(
        &mut self,
        py: Python<'_>,
        decision: Py<PyAny>,
        snapshot: Py<PyAny>,
        payload: Py<PyAny>,
    ) -> PyResult<()> {
        let (row, ts, spot, l0_version) = parse_append_inputs(py, &decision.bind(py), &snapshot.bind(py), &payload.bind(py))?;
        let store_date = et_date(ts);
        self.cleanup_retention_if_needed(&store_date)?;
        if !crate::research_store_support::is_rth(ts) {
            self.non_rth_ticks_skipped = self.non_rth_ticks_skipped.saturating_add(1);
            return Ok(());
        }
        if self.last_persist_second == Some(ts.timestamp()) {
            return Ok(());
        }
        let mut day_rows = self.load_canonical_day(py, &store_date)?;
        self.update_pending_labels(py, ts, spot, &mut day_rows)?;
        day_rows.push(row);
        if let Err(err) = self.persist_day_rows(py, &store_date, &PyList::new(py, day_rows.iter())?) {
            self.write_failures = self.write_failures.saturating_add(1);
            return Err(err);
        }
        self.last_persist_second = Some(ts.timestamp());
        self.rows_persisted_today = day_rows.len() as u64;
        self.last_persist_et = Some(ts.to_rfc3339());
        self.pending_labels
            .entry(pending_key(ts, l0_version, "SPY"))
            .or_insert_with(|| PendingOutcome::new(ts, l0_version, "SPY".into(), spot));
        Ok(())
    }

    #[pyo3(signature = (*, start, end, view="feature", fields=None, interval="1s", fmt="jsonl"))]
    fn query(
        &mut self,
        py: Python<'_>,
        start: &str,
        end: &str,
        view: &str,
        fields: Option<Vec<String>>,
        interval: &str,
        fmt: &str,
    ) -> PyResult<Py<PyDict>> {
        validate_query(view, interval, fmt)?;
        let start_dt = parse_ts_text(start).ok_or_else(|| PyValueError::new_err("invalid start/end timestamp"))?;
        let end_dt = parse_ts_text(end).ok_or_else(|| PyValueError::new_err("invalid start/end timestamp"))?;
        if end_dt < start_dt {
            return err_dict(py, "end must be >= start");
        }
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
            out.set_item("content_type", "application/x-parquet")?;
            out.set_item("bytes", l0_rust(py)?.call_method1("service_research_records_to_parquet", (PyList::new(py, records.iter())?,))?)?;
        } else {
            out.set_item("records", PyList::new(py, records.drain(..))?)?;
        }
        Ok(out.unbind())
    }

    fn get_export_job(&self, py: Python<'_>, job_id: &str) -> PyResult<Option<Py<PyDict>>> {
        Ok(self.jobs.get(job_id).map(|job| job_dict(py, job)))
    }

    fn read_export(&self, _py: Python<'_>, job_id: &str) -> PyResult<Option<(String, Vec<u8>)>> {
        let Some(job) = self.jobs.get(job_id) else {
            return Ok(None);
        };
        if job.status != "done" {
            return Ok(None);
        }
        let bytes = fs::read(&job.path).map_err(|err| PyValueError::new_err(err.to_string()))?;
        let content_type = if job.path.ends_with(".parquet") { "application/x-parquet" } else { "application/x-ndjson" };
        Ok(Some((content_type.to_string(), bytes)))
    }

    #[pyo3(signature = (*, count, view, fields=None))]
    fn latest_feature_view(
        &self,
        py: Python<'_>,
        count: usize,
        view: &str,
        fields: Option<Vec<String>>,
    ) -> PyResult<Vec<Py<PyAny>>> {
        let mut records = crate::research_store_io::load_latest(py, &self.canonical_dir, "day", count.max(256))?;
        if view == "compact" {
            records = self.to_compact(py, records)?;
        } else if let Some(field_list) = fields {
            records = self.project_fields(py, records, view, field_list)?;
        } else {
            records = self.project_fields(py, records, view, ResearchFeatureStore::latest_feature_fields(py)?)?;
        }
        Ok(if count > 0 && records.len() > count { records.split_off(records.len() - count) } else { records })
    }

    fn diagnostics(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let out = PyDict::new(py);
        out.set_item("root", self.root.to_string_lossy().to_string())?;
        out.set_item("pending_labels", self.pending_labels.len())?;
        out.set_item("export_jobs", self.jobs.len())?;
        out.set_item("canonical_retention_days", self.canonical_retention_days)?;
        out.set_item("rows_persisted_today", self.rows_persisted_today)?;
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
        let data: Vec<u8> = if fmt == "parquet" {
            l0_rust(py)?.call_method1("service_research_records_to_parquet", (PyList::new(py, records.iter())?,))?.extract()?
        } else {
            l0_rust(py)?.call_method1("service_research_jsonl_bytes", (PyList::new(py, records.iter())?,))?.extract()?
        };
        fs::write(&path, data).map_err(|err| PyValueError::new_err(err.to_string()))?;
        self.jobs.insert(job_id.clone(), ExportJob { status: "done".into(), path: path.to_string_lossy().to_string(), format: fmt.into(), error: None });
        Ok(job_id)
    }

    fn load_canonical_day(&self, py: Python<'_>, date_str: &str) -> PyResult<Vec<Py<PyAny>>> {
        let path = self.canonical_dir.join(format!("day_{date_str}.parquet"));
        if !path.exists() {
            return Ok(Vec::new());
        }
        let rows = l0_rust(py)?.call_method1("service_research_read_parquet_rows", (path.to_string_lossy().to_string(),))?;
        Ok(rows.downcast::<PyList>()?.iter().map(|row| row.unbind()).collect())
    }

    fn persist_day_rows(&self, py: Python<'_>, date_str: &str, rows: &Bound<'_, PyList>) -> PyResult<()> {
        let path = self.canonical_dir.join(format!("day_{date_str}.parquet"));
        l0_rust(py)?.call_method1("service_research_write_parquet_rows", (path.to_string_lossy().to_string(), rows, tier_schema(py, "canonical")?))?;
        Ok(())
    }

    fn cleanup_retention_if_needed(&mut self, date_str: &str) -> PyResult<()> {
        if self.last_cleanup_date.as_deref() == Some(date_str) {
            return Ok(());
        }
        self.last_cleanup_date = Some(date_str.to_string());
        cleanup_tier_path(&self.canonical_dir, "day", parse_date(date_str)?, self.canonical_retention_days)
    }
}

fn default_setting<T>(py: Python<'_>, name: &str, default: T) -> PyResult<T>
where
    T: Clone + for<'a> FromPyObject<'a>,
{
    Ok(py.import("shared.config")?.getattr("settings")?.getattr(name)?.extract::<T>().unwrap_or(default))
}

fn validate_query(view: &str, interval: &str, fmt: &str) -> PyResult<()> {
    if !VALID_VIEWS.contains(&view) || view == "audit" {
        return Err(PyValueError::new_err("invalid view"));
    }
    if !VALID_FORMATS.contains(&fmt) {
        return Err(PyValueError::new_err("invalid format"));
    }
    if !VALID_INTERVALS.iter().any(|(name, _)| *name == interval) {
        return Err(PyValueError::new_err("invalid interval"));
    }
    Ok(())
}

fn parse_date(text: &str) -> PyResult<chrono::NaiveDate> {
    chrono::NaiveDate::parse_from_str(text, "%Y%m%d")
        .or_else(|_| chrono::NaiveDate::parse_from_str(text, "%Y-%m-%d"))
        .map_err(|err| PyValueError::new_err(err.to_string()))
}

fn path_obj(py: Python<'_>, path: &PathBuf) -> PyResult<Py<PyAny>> {
    Ok(py.import("pathlib")?.getattr("Path")?.call1((path.to_string_lossy().to_string(),))?.unbind())
}

fn job_dict(py: Python<'_>, job: &ExportJob) -> Py<PyDict> {
    let out = PyDict::new(py);
    let _ = out.set_item("status", &job.status);
    let _ = out.set_item("path", &job.path);
    let _ = out.set_item("format", &job.format);
    if let Some(error) = &job.error {
        let _ = out.set_item("error", error);
    }
    out.unbind()
}

fn err_dict(py: Python<'_>, message: &str) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("error", message)?;
    Ok(out.unbind())
}

pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ResearchFeatureStore>()?;
    Ok(())
}
