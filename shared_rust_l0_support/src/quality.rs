use crate::events::DataQualityAlert;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::VecDeque;
use std::time::{SystemTime, UNIX_EPOCH};

fn now_secs() -> f64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0)
}

#[pyclass(module = "shared_rust.services_l0_support")]
#[derive(Clone)]
pub struct DataQualityReport {
    #[pyo3(get, set)] pub symbol: String,
    #[pyo3(get, set)] pub passed: bool,
    #[pyo3(get, set)] pub warnings: Vec<String>,
    #[pyo3(get, set)] pub errors: Vec<String>,
    #[pyo3(get, set)] pub nan_fields: Vec<String>,
    #[pyo3(get, set)] pub timestamp: f64,
}
#[pymethods]
impl DataQualityReport {
    #[new]
    #[pyo3(signature = (symbol, passed=false, warnings=None, errors=None, nan_fields=None, timestamp=None))]
    pub fn new(symbol: String, passed: bool, warnings: Option<Vec<String>>, errors: Option<Vec<String>>, nan_fields: Option<Vec<String>>, timestamp: Option<f64>) -> Self {
        Self { symbol, passed, warnings: warnings.unwrap_or_default(), errors: errors.unwrap_or_default(), nan_fields: nan_fields.unwrap_or_default(), timestamp: timestamp.unwrap_or_else(now_secs) }
    }
    pub fn add_warning(&mut self, msg: String) { self.warnings.push(msg); }
    pub fn add_error(&mut self, msg: String) { self.errors.push(msg); self.passed = false; }
    #[getter] fn has_issues(&self) -> bool { !(self.warnings.is_empty() && self.errors.is_empty()) }
    #[getter] fn is_clean(&self) -> bool { self.passed && self.errors.is_empty() }
    fn summary(&self) -> String {
        let mut parts = Vec::new();
        if !self.errors.is_empty() { parts.push(format!("ERR:{}", self.errors.len())); }
        if !self.warnings.is_empty() { parts.push(format!("WARN:{}", self.warnings.len())); }
        format!("[{}] {} {}", self.symbol, if self.passed {"PASS"} else {"FAIL"}, parts.join(" ")).trim().to_string()
    }
}

#[pyclass(module = "shared_rust.services_l0_support")]
#[derive(Clone, Default)]
pub struct QualityMetrics {
    #[pyo3(get, set)] pub total_ticks: usize,
    #[pyo3(get, set)] pub passed_ticks: usize,
    #[pyo3(get, set)] pub nan_count: usize,
    #[pyo3(get, set)] pub gap_events: usize,
    #[pyo3(get, set)] pub breaker_trips: usize,
    #[pyo3(get, set)] pub oi_surges: usize,
}
#[pymethods]
impl QualityMetrics {
    #[new]
    #[pyo3(signature = (total_ticks=0, passed_ticks=0, nan_count=0, gap_events=0, breaker_trips=0, oi_surges=0))]
    pub fn new(total_ticks: usize, passed_ticks: usize, nan_count: usize, gap_events: usize, breaker_trips: usize, oi_surges: usize) -> Self {
        Self { total_ticks, passed_ticks, nan_count, gap_events, breaker_trips, oi_surges }
    }
    #[getter] fn pass_rate(&self) -> f64 { if self.total_ticks == 0 { 0.0 } else { self.passed_ticks as f64 / self.total_ticks as f64 } }
    #[getter] fn nan_rate(&self) -> f64 { if self.total_ticks == 0 { 0.0 } else { self.nan_count as f64 / self.total_ticks as f64 } }
    fn to_dict(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let d = PyDict::new(py);
        d.set_item("total_ticks", self.total_ticks)?; d.set_item("pass_rate", self.pass_rate())?; d.set_item("nan_rate", self.nan_rate())?;
        d.set_item("gap_events", self.gap_events)?; d.set_item("breaker_trips", self.breaker_trips)?; d.set_item("oi_surges", self.oi_surges)?;
        Ok(d.unbind())
    }
}

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct QualityCollector {
    window_size: usize,
    reports: VecDeque<DataQualityReport>,
}
#[pymethods]
impl QualityCollector {
    #[new]
    #[pyo3(signature = (window_size=1000))]
    fn new(window_size: usize) -> Self { Self { window_size, reports: VecDeque::with_capacity(window_size) } }
    fn record(&mut self, report: PyRef<'_, DataQualityReport>) {
        if self.reports.len() == self.window_size { self.reports.pop_front(); }
        self.reports.push_back(report.clone());
    }
    #[pyo3(signature = (symbol=None))]
    fn snapshot(&self, symbol: Option<&str>) -> QualityMetrics {
        let mut m = QualityMetrics::default();
        for r in &self.reports {
            if symbol.is_some() && symbol != Some(r.symbol.as_str()) { continue; }
            m.total_ticks += 1;
            if r.passed { m.passed_ticks += 1; }
            m.nan_count += r.nan_fields.len();
            for w in &r.warnings {
                if w.contains("gap") { m.gap_events += 1; }
                else if w.contains("oi_surge") { m.oi_surges += 1; }
            }
            for e in &r.errors {
                let lower = e.to_lowercase();
                if lower.contains("breaker") || lower.contains("circuit") { m.breaker_trips += 1; }
            }
        }
        m
    }
    fn clear(&mut self) { self.reports.clear(); }
}

pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    let _ = std::any::TypeId::of::<DataQualityAlert>();
    m.add_class::<DataQualityReport>()?;
    m.add_class::<QualityMetrics>()?;
    m.add_class::<QualityCollector>()?;
    Ok(())
}
