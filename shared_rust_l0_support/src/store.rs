use crate::events::{CleanDepthEvent, CleanQuoteEvent};
use pyo3::prelude::*;
use std::collections::{HashMap, VecDeque};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

fn now_secs() -> f64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0)
}

#[pyclass(module = "shared_rust.services_l0_support")]
#[derive(Clone)]
pub struct SnapshotVersion {
    #[pyo3(get)] pub version: u64,
    #[pyo3(get)] pub created_at: f64,
    #[pyo3(get)] pub seq_no: i64,
    #[pyo3(get)] pub source: String,
}
#[pymethods]
impl SnapshotVersion {
    #[new]
    #[pyo3(signature = (version, created_at=None, seq_no=0, source="unknown"))]
    fn new(version: u64, created_at: Option<f64>, seq_no: i64, source: &str) -> Self { Self { version, created_at: created_at.unwrap_or_else(now_secs), seq_no, source: source.to_string() } }
}

#[pyclass(module = "shared_rust.services_l0_support")]
#[derive(Clone)]
pub struct FrozenSnapshot {
    #[pyo3(get)] pub version_meta: SnapshotVersion,
    #[pyo3(get)] pub spot_price: f64,
    #[pyo3(get)] pub spot_timestamp: f64,
    #[pyo3(get)] pub atm_strike: Option<f64>,
    #[pyo3(get)] pub chain_snapshot: Vec<(String, f64, f64, f64, Option<f64>)>,
    #[pyo3(get)] pub last_nan_count: usize,
    #[pyo3(get)] pub last_breaker_trips: usize,
}
#[pymethods]
impl FrozenSnapshot {
    #[getter] fn version(&self) -> u64 { self.version_meta.version }
    #[getter] fn age_ms(&self) -> f64 { (now_secs() - self.version_meta.created_at) * 1000.0 }
    #[pyo3(signature = (max_age_ms=2000.0))]
    fn is_fresh(&self, max_age_ms: f64) -> bool { self.age_ms() <= max_age_ms }
}

#[derive(Default, Clone)]
struct ChainEntry { bid: f64, ask: f64, open_interest: f64, delta: Option<f64> }
#[derive(Default)]
struct StoreInner { keep_versions: usize, version: u64, current: Option<FrozenSnapshot>, history: VecDeque<FrozenSnapshot>, spot_price: f64, spot_timestamp: f64, atm_strike: Option<f64>, chain: HashMap<String, ChainEntry>, nan_count: usize, breaker_trips: usize }

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct MVCCChainStateStore { inner: Mutex<StoreInner> }
#[pymethods]
impl MVCCChainStateStore {
    #[new]
    #[pyo3(signature = (keep_versions=3))]
    fn new(keep_versions: usize) -> Self { Self { inner: Mutex::new(StoreInner { keep_versions, history: VecDeque::with_capacity(keep_versions), ..Default::default() }) } }
    #[pyo3(signature = (price, timestamp=None))]
    fn update_spot(&self, price: f64, timestamp: Option<f64>) {
        if let Ok(mut inner) = self.inner.lock() {
            inner.spot_price = price;
            inner.spot_timestamp = timestamp.unwrap_or_else(now_secs);
            commit(&mut inner, 0, "spot");
        }
    }
    fn apply_depth(&self, event: PyRef<'_, CleanDepthEvent>) {
        if let Ok(mut inner) = self.inner.lock() {
            let entry = inner.chain.entry(event.symbol.clone()).or_default();
            entry.bid = event.bid.unwrap_or(entry.bid);
            entry.ask = event.ask.unwrap_or(entry.ask);
            commit(&mut inner, event.seq_no, "depth");
        }
    }
    fn apply_quote(&self, event: PyRef<'_, CleanQuoteEvent>) {
        if let Ok(mut inner) = self.inner.lock() {
            let entry = inner.chain.entry(event.symbol.clone()).or_default();
            entry.bid = event.bid;
            entry.ask = event.ask;
            entry.open_interest = event.open_interest;
            entry.delta = event.delta;
            commit(&mut inner, event.seq_no, "quote");
        }
    }
    #[pyo3(signature = (symbol, greeks, seq_no=None))]
    fn apply_greeks(&self, symbol: String, greeks: HashMap<String, f64>, seq_no: Option<i64>) {
        if let Ok(mut inner) = self.inner.lock() {
            let entry = inner.chain.entry(symbol).or_default();
            entry.delta = greeks.get("delta").copied().or(entry.delta);
            commit(&mut inner, seq_no.unwrap_or(0), "greeks");
        }
    }
    fn record_nan(&self) {
        if let Ok(mut inner) = self.inner.lock() {
            inner.nan_count += 1;
        }
    }
    fn record_breaker_trip(&self) {
        if let Ok(mut inner) = self.inner.lock() {
            inner.breaker_trips += 1;
        }
    }
    fn get_snapshot(&self) -> (u64, Option<FrozenSnapshot>) {
        if let Ok(inner) = self.inner.lock() {
            (inner.current.as_ref().map(|s| s.version()).unwrap_or(0), inner.current.clone())
        } else {
            (0, None)
        }
    }
    fn get_history(&self) -> Vec<FrozenSnapshot> {
        if let Ok(inner) = self.inner.lock() {
            inner.history.iter().cloned().collect()
        } else {
            Vec::new()
        }
    }
}

fn commit(inner: &mut StoreInner, seq_no: i64, source: &str) {
    inner.version += 1;
    let version_meta = SnapshotVersion::new(inner.version, Some(now_secs()), seq_no, source);
    let chain_snapshot = inner.chain.iter().map(|(sym, entry)| (sym.clone(), entry.bid, entry.ask, entry.open_interest, entry.delta)).collect::<Vec<_>>();
    let snap = FrozenSnapshot { version_meta, spot_price: inner.spot_price, spot_timestamp: inner.spot_timestamp, atm_strike: inner.atm_strike, chain_snapshot, last_nan_count: inner.nan_count, last_breaker_trips: inner.breaker_trips };
    if let Some(old) = inner.current.replace(snap) {
        if inner.history.len() == inner.keep_versions { inner.history.pop_front(); }
        inner.history.push_back(old);
    }
}

pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<SnapshotVersion>()?;
    m.add_class::<FrozenSnapshot>()?;
    m.add_class::<MVCCChainStateStore>()?;
    Ok(())
}
