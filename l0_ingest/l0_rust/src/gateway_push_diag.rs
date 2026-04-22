use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::VecDeque;
use std::sync::{Arc, Mutex};
use std::time::{Duration as StdDuration, Instant};
use time::{format_description::well_known::Rfc3339, OffsetDateTime};

const RAW_EVENT_WINDOW_1S: StdDuration = StdDuration::from_secs(1);
const RAW_EVENT_WINDOW_5S: StdDuration = StdDuration::from_secs(5);

#[derive(Default)]
pub struct RawSpyPushDiagnostics {
    quote_events: VecDeque<Instant>,
    depth_events: VecDeque<Instant>,
    last_quote_instant: Option<Instant>,
    last_depth_instant: Option<Instant>,
    last_raw_quote_gap_ms: Option<f64>,
    last_raw_depth_gap_ms: Option<f64>,
    last_raw_quote_timestamp_utc: Option<String>,
    last_raw_depth_timestamp_utc: Option<String>,
}

pub struct RawSpyPushSnapshot {
    pub raw_quote_event_count_1s: usize,
    pub raw_quote_event_count_5s: usize,
    pub raw_depth_event_count_1s: usize,
    pub raw_depth_event_count_5s: usize,
    pub last_raw_quote_gap_ms: Option<f64>,
    pub last_raw_depth_gap_ms: Option<f64>,
    pub last_raw_quote_timestamp_utc: Option<String>,
    pub last_raw_depth_timestamp_utc: Option<String>,
}

#[pyclass]
pub struct GatewayPushDiagnosticsHandle {
    diag: Arc<Mutex<RawSpyPushDiagnostics>>,
}

pub fn new_shared_diag() -> Arc<Mutex<RawSpyPushDiagnostics>> {
    Arc::new(Mutex::new(RawSpyPushDiagnostics::default()))
}

pub fn record_quote(diag: &Arc<Mutex<RawSpyPushDiagnostics>>, symbol: &str) {
    if symbol != "SPY.US" {
        return;
    }
    if let Ok(mut inner) = diag.lock() {
        inner.record_quote();
    }
}

pub fn record_depth(diag: &Arc<Mutex<RawSpyPushDiagnostics>>, symbol: &str) {
    if symbol != "SPY.US" {
        return;
    }
    if let Ok(mut inner) = diag.lock() {
        inner.record_depth();
    }
}

pub fn reset(diag: &Arc<Mutex<RawSpyPushDiagnostics>>) {
    if let Ok(mut inner) = diag.lock() {
        inner.reset();
    }
}

pub fn snapshot_to_pyobject(
    py: Python<'_>,
    diag: &Arc<Mutex<RawSpyPushDiagnostics>>,
) -> PyResult<PyObject> {
    let snapshot = match diag.lock() {
        Ok(mut inner) => inner.snapshot(),
        Err(_) => RawSpyPushSnapshot::default(),
    };
    let out = PyDict::new(py);
    out.set_item("raw_quote_event_count_1s", snapshot.raw_quote_event_count_1s)?;
    out.set_item("raw_quote_event_count_5s", snapshot.raw_quote_event_count_5s)?;
    out.set_item("raw_depth_event_count_1s", snapshot.raw_depth_event_count_1s)?;
    out.set_item("raw_depth_event_count_5s", snapshot.raw_depth_event_count_5s)?;
    out.set_item("last_raw_quote_gap_ms", snapshot.last_raw_quote_gap_ms)?;
    out.set_item("last_raw_depth_gap_ms", snapshot.last_raw_depth_gap_ms)?;
    out.set_item("last_raw_quote_timestamp_utc", snapshot.last_raw_quote_timestamp_utc)?;
    out.set_item("last_raw_depth_timestamp_utc", snapshot.last_raw_depth_timestamp_utc)?;
    Ok(out.into_any().unbind())
}

impl GatewayPushDiagnosticsHandle {
    pub fn new(diag: Arc<Mutex<RawSpyPushDiagnostics>>) -> Self {
        Self { diag }
    }
}

#[pymethods]
impl GatewayPushDiagnosticsHandle {
    fn snapshot(&self, py: Python<'_>) -> PyResult<PyObject> {
        snapshot_to_pyobject(py, &self.diag)
    }
}

impl RawSpyPushDiagnostics {
    fn reset(&mut self) {
        self.quote_events.clear();
        self.depth_events.clear();
        self.last_quote_instant = None;
        self.last_depth_instant = None;
        self.last_raw_quote_gap_ms = None;
        self.last_raw_depth_gap_ms = None;
        self.last_raw_quote_timestamp_utc = None;
        self.last_raw_depth_timestamp_utc = None;
    }

    fn record_quote(&mut self) {
        let now = Instant::now();
        if let Some(last) = self.last_quote_instant {
            self.last_raw_quote_gap_ms = Some(now.duration_since(last).as_secs_f64() * 1000.0);
        }
        self.last_quote_instant = Some(now);
        self.last_raw_quote_timestamp_utc = Some(now_utc_iso());
        self.quote_events.push_back(now);
        self.trim(now);
    }

    fn record_depth(&mut self) {
        let now = Instant::now();
        if let Some(last) = self.last_depth_instant {
            self.last_raw_depth_gap_ms = Some(now.duration_since(last).as_secs_f64() * 1000.0);
        }
        self.last_depth_instant = Some(now);
        self.last_raw_depth_timestamp_utc = Some(now_utc_iso());
        self.depth_events.push_back(now);
        self.trim(now);
    }

    fn snapshot(&mut self) -> RawSpyPushSnapshot {
        let now = Instant::now();
        self.trim(now);
        RawSpyPushSnapshot {
            raw_quote_event_count_1s: self.count_recent(&self.quote_events, RAW_EVENT_WINDOW_1S, now),
            raw_quote_event_count_5s: self.quote_events.len(),
            raw_depth_event_count_1s: self.count_recent(&self.depth_events, RAW_EVENT_WINDOW_1S, now),
            raw_depth_event_count_5s: self.depth_events.len(),
            last_raw_quote_gap_ms: self.last_raw_quote_gap_ms,
            last_raw_depth_gap_ms: self.last_raw_depth_gap_ms,
            last_raw_quote_timestamp_utc: self.last_raw_quote_timestamp_utc.clone(),
            last_raw_depth_timestamp_utc: self.last_raw_depth_timestamp_utc.clone(),
        }
    }

    fn trim(&mut self, now: Instant) {
        let cutoff = now.checked_sub(RAW_EVENT_WINDOW_5S);
        while matches!(self.quote_events.front(), Some(ts) if cutoff.map(|v| *ts < v).unwrap_or(false)) {
            self.quote_events.pop_front();
        }
        while matches!(self.depth_events.front(), Some(ts) if cutoff.map(|v| *ts < v).unwrap_or(false)) {
            self.depth_events.pop_front();
        }
    }

    fn count_recent(
        &self,
        events: &VecDeque<Instant>,
        window: StdDuration,
        now: Instant,
    ) -> usize {
        let cutoff = now.checked_sub(window);
        events
            .iter()
            .filter(|ts| cutoff.map(|v| **ts >= v).unwrap_or(true))
            .count()
    }
}

impl Default for RawSpyPushSnapshot {
    fn default() -> Self {
        Self {
            raw_quote_event_count_1s: 0,
            raw_quote_event_count_5s: 0,
            raw_depth_event_count_1s: 0,
            raw_depth_event_count_5s: 0,
            last_raw_quote_gap_ms: None,
            last_raw_depth_gap_ms: None,
            last_raw_quote_timestamp_utc: None,
            last_raw_depth_timestamp_utc: None,
        }
    }
}

fn now_utc_iso() -> String {
    match OffsetDateTime::now_utc().format(&Rfc3339) {
        Ok(value) => value,
        Err(_) => OffsetDateTime::now_utc().to_string(),
    }
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<GatewayPushDiagnosticsHandle>()?;
    Ok(())
}
