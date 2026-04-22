use crate::research_store_support::{l0_rust, parse_ts_any, utc_iso};
use chrono::{DateTime, Utc};
use pyo3::{
    exceptions::PyValueError,
    prelude::*,
    types::{PyDict, PyList},
};
use std::{
    collections::{HashMap, HashSet},
    fs,
    path::PathBuf,
};

const HORIZONS: [(&str, f64); 4] = [("1m", 60.0), ("5m", 300.0), ("15m", 900.0), ("60m", 3600.0)];
const LABEL_HORIZON_SECONDS: f64 = 3600.0;

#[derive(Clone, Default)]
pub struct PendingOutcome {
    pub ts: DateTime<Utc>,
    pub l0_version: i64,
    pub symbol: String,
    pub base_spot: f64,
    pub last_spot: f64,
    pub min_ret: f64,
    pub log_returns: Vec<f64>,
    pub fwd_ret: HashMap<String, Option<f64>>,
}

pub struct PendingReplayResult {
    pub pending_labels: HashMap<String, PendingOutcome>,
    pub recovered_rows: Vec<Py<PyAny>>,
    pub replay_date: Option<String>,
}

#[derive(Clone)]
struct FeaturePoint {
    ts: DateTime<Utc>,
    l0_version: i64,
    symbol: String,
    spot: f64,
}

impl PendingOutcome {
    pub fn new(ts: DateTime<Utc>, l0_version: i64, symbol: String, spot: f64) -> Self {
        Self {
            ts,
            l0_version,
            symbol,
            base_spot: spot,
            last_spot: spot,
            min_ret: 0.0,
            log_returns: Vec::new(),
            fwd_ret: horizon_map(),
        }
    }

    pub fn advance(&mut self, ts: DateTime<Utc>, spot: f64) {
        let elapsed = self.elapsed_seconds(ts);
        let current_ret = (spot / self.base_spot) - 1.0;
        self.min_ret = self.min_ret.min(current_ret);
        if self.last_spot > 0.0 && spot > 0.0 {
            self.log_returns.push((spot / self.last_spot).ln());
        }
        self.last_spot = spot;
        for (horizon, seconds) in HORIZONS {
            if self.fwd_ret[horizon].is_none() && elapsed >= seconds {
                self.fwd_ret.insert(horizon.to_string(), Some(current_ret));
            }
        }
    }

    pub fn elapsed_seconds(&self, ts: DateTime<Utc>) -> f64 {
        (ts - self.ts).num_seconds().max(0) as f64
    }

    pub fn matured(&self, ts: DateTime<Utc>) -> bool {
        self.elapsed_seconds(ts) >= LABEL_HORIZON_SECONDS
    }

    pub fn label_value(&self, horizon: &str) -> Option<f64> {
        self.fwd_ret.get(horizon).copied().flatten()
    }
}

pub fn pending_key(ts: DateTime<Utc>, l0_version: i64, symbol: &str) -> String {
    format!("{}|{}|{symbol}", ts.to_rfc3339(), l0_version)
}

pub fn recover_latest_feature_day(
    py: Python<'_>,
    feature_dir: &PathBuf,
    label_dir: &PathBuf,
) -> PyResult<PendingReplayResult> {
    let Some(date_str) = latest_feature_date(py, feature_dir)? else {
        return Ok(PendingReplayResult {
            pending_labels: HashMap::new(),
            recovered_rows: Vec::new(),
            replay_date: None,
        });
    };
    let feature_path = feature_dir.join(format!("feature_{date_str}.parquet"));
    let label_path = label_dir.join(format!("label_{date_str}.parquet"));
    let points = load_feature_points(py, &feature_path)?;
    let mut label_keys = load_label_keys(py, &label_path)?;
    let native = l0_rust(py)?;
    let mut pending_labels: HashMap<String, PendingOutcome> = HashMap::new();
    let mut recovered_rows = Vec::new();

    for point in points {
        let mut matured_keys = Vec::new();
        for (key, state) in pending_labels.iter_mut() {
            state.advance(point.ts, point.spot);
            if state.matured(point.ts) {
                if !label_keys.contains(key) {
                    recovered_rows.push(
                        native
                            .call_method1(
                                "service_research_label_row",
                                (
                                    utc_iso(state.ts),
                                    state.l0_version,
                                    state.symbol.clone(),
                                    utc_iso(Utc::now()),
                                    state.label_value("1m"),
                                    state.label_value("5m"),
                                    state.label_value("15m"),
                                    state.label_value("60m"),
                                    state.min_ret,
                                    realized_volatility(&state.log_returns),
                                    state.elapsed_seconds(point.ts),
                                ),
                            )?
                            .unbind(),
                    );
                    label_keys.insert(key.clone());
                }
                matured_keys.push(key.clone());
            }
        }
        for key in matured_keys {
            pending_labels.remove(&key);
        }

        let key = pending_key(point.ts, point.l0_version, &point.symbol);
        if !label_keys.contains(&key) {
            pending_labels.insert(
                key,
                PendingOutcome::new(point.ts, point.l0_version, point.symbol, point.spot),
            );
        }
    }

    Ok(PendingReplayResult {
        pending_labels,
        recovered_rows,
        replay_date: Some(date_str),
    })
}

fn horizon_map() -> HashMap<String, Option<f64>> {
    HORIZONS
        .into_iter()
        .map(|(name, _)| (name.to_string(), None))
        .collect()
}

fn latest_feature_date(py: Python<'_>, feature_dir: &PathBuf) -> PyResult<Option<String>> {
    let native = l0_rust(py)?;
    let names: Vec<String> = fs::read_dir(feature_dir)
        .map_err(|err| PyValueError::new_err(err.to_string()))?
        .filter_map(Result::ok)
        .filter_map(|entry| entry.file_name().into_string().ok())
        .collect();
    let files = native
        .call_method1("service_research_latest_files", (names, "feature"))?
        .downcast_into::<PyList>()?;
    if files.is_empty() {
        return Ok(None);
    }
    let latest = files.get_item(0)?.extract::<String>()?;
    Ok(parse_date_from_file_name("feature", &latest))
}

fn parse_date_from_file_name(prefix: &str, file_name: &str) -> Option<String> {
    file_name
        .strip_prefix(&format!("{prefix}_"))
        .and_then(|value| value.strip_suffix(".parquet"))
        .map(ToOwned::to_owned)
}

fn load_feature_points(py: Python<'_>, feature_path: &PathBuf) -> PyResult<Vec<FeaturePoint>> {
    let rows = read_rows(py, feature_path)?;
    let mut points = Vec::with_capacity(rows.len());
    for row in rows {
        let dict = row.bind(py).downcast::<PyDict>()?;
        let ts = dict
            .get_item("data_timestamp")?
            .and_then(|value| parse_ts_any(&value).ok().flatten())
            .ok_or_else(|| PyValueError::new_err("feature row missing valid data_timestamp"))?;
        let l0_version = dict
            .get_item("l0_version")?
            .ok_or_else(|| PyValueError::new_err("feature row missing l0_version"))?
            .extract::<i64>()?;
        let symbol = dict
            .get_item("symbol")?
            .ok_or_else(|| PyValueError::new_err("feature row missing symbol"))?
            .extract::<String>()?;
        let spot = dict
            .get_item("spot")?
            .ok_or_else(|| PyValueError::new_err("feature row missing spot"))?
            .extract::<f64>()?;
        if !spot.is_finite() || spot <= 0.0 {
            return Err(PyValueError::new_err("feature row has invalid spot"));
        }
        points.push(FeaturePoint {
            ts,
            l0_version,
            symbol,
            spot,
        });
    }
    points.sort_by_key(|point| point.ts);
    Ok(points)
}

fn load_label_keys(py: Python<'_>, label_path: &PathBuf) -> PyResult<HashSet<String>> {
    let rows = read_rows(py, label_path)?;
    let mut keys = HashSet::with_capacity(rows.len());
    for row in rows {
        let dict = row.bind(py).downcast::<PyDict>()?;
        let ts = dict
            .get_item("data_timestamp")?
            .and_then(|value| parse_ts_any(&value).ok().flatten())
            .ok_or_else(|| PyValueError::new_err("label row missing valid data_timestamp"))?;
        let l0_version = dict
            .get_item("l0_version")?
            .ok_or_else(|| PyValueError::new_err("label row missing l0_version"))?
            .extract::<i64>()?;
        let symbol = dict
            .get_item("symbol")?
            .ok_or_else(|| PyValueError::new_err("label row missing symbol"))?
            .extract::<String>()?;
        keys.insert(pending_key(ts, l0_version, &symbol));
    }
    Ok(keys)
}

fn read_rows(py: Python<'_>, path: &PathBuf) -> PyResult<Vec<Py<PyAny>>> {
    if !path.exists() {
        return Ok(Vec::new());
    }
    let native = l0_rust(py)?;
    let rows = native.call_method1("service_research_read_parquet_rows", (path.to_string_lossy().to_string(),))?;
    Ok(rows.downcast::<PyList>()?.iter().map(|row| row.unbind()).collect())
}

fn realized_volatility(values: &[f64]) -> f64 {
    if values.len() < 2 {
        return 0.0;
    }
    let mean = values.iter().sum::<f64>() / values.len() as f64;
    let var = values
        .iter()
        .map(|value| (value - mean).powi(2))
        .sum::<f64>()
        / (values.len() as f64 - 1.0);
    var.max(0.0).sqrt()
}
