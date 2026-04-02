use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::time::{SystemTime, UNIX_EPOCH};

fn now_secs() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

#[pyclass(frozen)]
pub struct EventType;
#[pymethods]
impl EventType {
    #[classattr]
    pub const QUOTE: &'static str = "quote";
    #[classattr]
    pub const DEPTH: &'static str = "depth";
    #[classattr]
    pub const TRADE: &'static str = "trade";
    #[classattr]
    pub const REST: &'static str = "rest";
    #[classattr]
    pub const SYSTEM: &'static str = "system";
}

#[pyclass(frozen)]
pub struct EventPriority;
#[pymethods]
impl EventPriority {
    #[classattr]
    pub const CRITICAL: i32 = 0;
    #[classattr]
    pub const HIGH: i32 = 1;
    #[classattr]
    pub const NORMAL: i32 = 2;
    #[classattr]
    pub const LOW: i32 = 3;
}

#[pyclass(frozen)]
pub struct QualityFlag;
#[pymethods]
impl QualityFlag {
    #[classattr]
    pub const OK: i32 = 0x00;
    #[classattr]
    pub const NAN_CLEANED: i32 = 0x01;
    #[classattr]
    pub const INF_CLAMPED: i32 = 0x02;
    #[classattr]
    pub const BID_GT_ASK: i32 = 0x04;
    #[classattr]
    pub const STALE: i32 = 0x08;
    #[classattr]
    pub const TICK_JUMP: i32 = 0x10;
    #[classattr]
    pub const OI_SURGE: i32 = 0x20;
    #[classattr]
    pub const ESTIMATED: i32 = 0x40;
    #[classattr]
    pub const REST_BACKFILL: i32 = 0x80;
}

#[pyclass(frozen)]
pub struct AlertSeverity;
#[pymethods]
impl AlertSeverity {
    #[classattr]
    pub const INFO: &'static str = "info";
    #[classattr]
    pub const WARNING: &'static str = "warning";
    #[classattr]
    pub const ERROR: &'static str = "error";
    #[classattr]
    pub const CRITICAL: &'static str = "critical";
}

#[pyclass(frozen)]
pub struct BreakerReason;
#[pymethods]
impl BreakerReason {
    #[classattr]
    pub const TICK_JUMP: &'static str = "tick_jump";
    #[classattr]
    pub const GAP_TIMEOUT: &'static str = "gap_timeout";
    #[classattr]
    pub const OI_SURGE: &'static str = "oi_surge";
    #[classattr]
    pub const BID_GT_ASK: &'static str = "bid_gt_ask";
    #[classattr]
    pub const HTTP_429: &'static str = "http_429";
    #[classattr]
    pub const CONSECUTIVE_FAIL: &'static str = "consecutive_fail";
}

#[pyclass(module = "shared_rust.services_l0_support", subclass)]
#[derive(Clone)]
pub struct BaseEvent {
    #[pyo3(get, set)] pub seq_no: i64,
    #[pyo3(get, set)] pub symbol: String,
    #[pyo3(get, set)] pub arrival_mono: f64,
    #[pyo3(get, set)] pub source: String,
    #[pyo3(get, set)] pub event_type: String,
    #[pyo3(get, set)] pub priority: i32,
}

#[pymethods]
impl BaseEvent {
    #[new]
    #[pyo3(signature = (seq_no, symbol, arrival_mono=None, source="longport_ws", event_type="system", priority=2))]
    pub fn new(seq_no: i64, symbol: String, arrival_mono: Option<f64>, source: &str, event_type: &str, priority: i32) -> Self {
        Self { seq_no, symbol, arrival_mono: arrival_mono.unwrap_or_else(now_secs), source: source.to_string(), event_type: event_type.to_string(), priority }
    }

    #[getter]
    fn age_ms(&self) -> f64 { (now_secs() - self.arrival_mono) * 1000.0 }
}

#[pyclass(module = "shared_rust.services_l0_support")]
#[derive(Clone)]
pub struct L2Level {
    #[pyo3(get, set)] pub price: f64,
    #[pyo3(get, set)] pub size: f64,
    #[pyo3(get, set)] pub order_count: i64,
}
#[pymethods]
impl L2Level {
    #[new]
    #[pyo3(signature = (price, size, order_count=0))]
    pub fn new(price: f64, size: f64, order_count: i64) -> Self { Self { price, size, order_count } }
}

#[pyclass(module = "shared_rust.services_l0_support")]
#[derive(Clone)]
pub struct CleanQuoteEvent {
    #[pyo3(get, set)] pub seq_no: i64,
    #[pyo3(get, set)] pub symbol: String,
    #[pyo3(get, set)] pub arrival_mono: f64,
    #[pyo3(get, set)] pub source: String,
    #[pyo3(get, set)] pub event_type: String,
    #[pyo3(get, set)] pub priority: i32,
    #[pyo3(get, set)] pub bid: f64,
    #[pyo3(get, set)] pub ask: f64,
    #[pyo3(get, set)] pub last: f64,
    #[pyo3(get, set)] pub volume: f64,
    #[pyo3(get, set)] pub open_interest: f64,
    #[pyo3(get, set)] pub delta: Option<f64>,
    #[pyo3(get, set)] pub gamma: Option<f64>,
    #[pyo3(get, set)] pub theta: Option<f64>,
    #[pyo3(get, set)] pub vega: Option<f64>,
    #[pyo3(get, set)] pub iv: Option<f64>,
    #[pyo3(get, set)] pub strike: Option<f64>,
    #[pyo3(get, set)] pub expiry: Option<String>,
    #[pyo3(get, set)] pub option_type: Option<String>,
    #[pyo3(get, set)] pub source_tier: i32,
    #[pyo3(get, set)] pub quality_flags: i32,
    #[pyo3(get, set)] pub version: i32,
}
#[pymethods]
impl CleanQuoteEvent {
    #[new]
    #[pyo3(signature = (seq_no, symbol, bid=0.0, ask=0.0, last=0.0, volume=0.0, open_interest=0.0, delta=None, gamma=None, theta=None, vega=None, iv=None, strike=None, expiry=None, option_type=None, source_tier=1, quality_flags=0, version=2, arrival_mono=None, source="longport_ws", event_type="quote", priority=2))]
    pub fn new(seq_no:i64,symbol:String,bid:f64,ask:f64,last:f64,volume:f64,open_interest:f64,delta:Option<f64>,gamma:Option<f64>,theta:Option<f64>,vega:Option<f64>,iv:Option<f64>,strike:Option<f64>,expiry:Option<String>,option_type:Option<String>,source_tier:i32,quality_flags:i32,version:i32,arrival_mono:Option<f64>,source:&str,event_type:&str,priority:i32)->Self{Self{seq_no,symbol,arrival_mono:arrival_mono.unwrap_or_else(now_secs),source:source.to_string(),event_type:event_type.to_string(),priority,bid,ask,last,volume,open_interest,delta,gamma,theta,vega,iv,strike,expiry,option_type,source_tier,quality_flags,version}}
    #[getter] fn mid(&self) -> f64 { if self.ask > 0.0 { (self.bid + self.ask) / 2.0 } else { self.last } }
    #[getter] fn spread(&self) -> f64 { (self.ask - self.bid).max(0.0) }
    fn has_flag(&self, flag: i32) -> bool { (self.quality_flags & flag) != 0 }
    fn to_legacy_dict(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let d = PyDict::new(py);
        d.set_item("bid", self.bid)?; d.set_item("ask", self.ask)?; d.set_item("last", self.last)?;
        d.set_item("volume", self.volume)?; d.set_item("open_interest", self.open_interest)?;
        d.set_item("delta", self.delta)?; d.set_item("gamma", self.gamma)?; d.set_item("theta", self.theta)?;
        d.set_item("vega", self.vega)?; d.set_item("iv", self.iv)?; d.set_item("strike", self.strike)?;
        d.set_item("expiry", self.expiry.clone())?; d.set_item("option_type", self.option_type.clone())?;
        Ok(d.unbind())
    }
}

#[pyclass(module = "shared_rust.services_l0_support")]
#[derive(Clone)]
pub struct CleanDepthEvent {
    #[pyo3(get, set)] pub seq_no: i64,
    #[pyo3(get, set)] pub symbol: String,
    #[pyo3(get, set)] pub arrival_mono: f64,
    #[pyo3(get, set)] pub source: String,
    #[pyo3(get, set)] pub event_type: String,
    #[pyo3(get, set)] pub priority: i32,
    #[pyo3(get, set)] pub bids: Vec<L2Level>,
    #[pyo3(get, set)] pub asks: Vec<L2Level>,
    #[pyo3(get, set)] pub bid: Option<f64>,
    #[pyo3(get, set)] pub ask: Option<f64>,
    #[pyo3(get, set)] pub bid_size: Option<f64>,
    #[pyo3(get, set)] pub ask_size: Option<f64>,
    #[pyo3(get, set)] pub source_tier: i32,
    #[pyo3(get, set)] pub quality_flags: i32,
    #[pyo3(get, set)] pub version: i32,
}
#[pymethods]
impl CleanDepthEvent {
    #[new]
    #[pyo3(signature = (seq_no, symbol, bids=None, asks=None, bid=None, ask=None, bid_size=None, ask_size=None, source_tier=1, quality_flags=0, version=2, arrival_mono=None, source="longport_ws", event_type="depth", priority=2))]
    pub fn new(seq_no:i64,symbol:String,bids:Option<Vec<L2Level>>,asks:Option<Vec<L2Level>>,bid:Option<f64>,ask:Option<f64>,bid_size:Option<f64>,ask_size:Option<f64>,source_tier:i32,quality_flags:i32,version:i32,arrival_mono:Option<f64>,source:&str,event_type:&str,priority:i32)->Self{
        let bids_v = bids.unwrap_or_default();
        let asks_v = asks.unwrap_or_default();
        let first_bid = bids_v.first().map(|x| x.price);
        let first_bid_size = bids_v.first().map(|x| x.size);
        let first_ask = asks_v.first().map(|x| x.price);
        let first_ask_size = asks_v.first().map(|x| x.size);
        Self{seq_no,symbol,arrival_mono:arrival_mono.unwrap_or_else(now_secs),source:source.to_string(),event_type:event_type.to_string(),priority,bids:bids_v,asks:asks_v,bid:bid.or(first_bid),ask:ask.or(first_ask),bid_size:bid_size.or(first_bid_size),ask_size:ask_size.or(first_ask_size),source_tier,quality_flags,version}
    }
    #[getter] fn mid(&self) -> Option<f64> { match (self.bid, self.ask) { (Some(b), Some(a)) => Some((b+a)/2.0), _ => None } }
    #[getter] fn depth_imbalance(&self) -> f64 { let buy:f64=self.bids.iter().map(|x|x.size).sum(); let sell:f64=self.asks.iter().map(|x|x.size).sum(); let total=buy+sell; if total>0.0 {(buy-sell)/total} else {0.0} }
}

#[pyclass(module = "shared_rust.services_l0_support")]
#[derive(Clone)]
pub struct CleanTradeEvent {
    #[pyo3(get, set)] pub seq_no: i64,
    #[pyo3(get, set)] pub symbol: String,
    #[pyo3(get, set)] pub arrival_mono: f64,
    #[pyo3(get, set)] pub source: String,
    #[pyo3(get, set)] pub event_type: String,
    #[pyo3(get, set)] pub priority: i32,
    #[pyo3(get, set)] pub price: f64,
    #[pyo3(get, set)] pub size: f64,
    #[pyo3(get, set)] pub direction: Option<String>,
    #[pyo3(get, set)] pub source_tier: i32,
    #[pyo3(get, set)] pub quality_flags: i32,
    #[pyo3(get, set)] pub version: i32,
}
#[pymethods]
impl CleanTradeEvent {
    #[new]
    #[pyo3(signature = (seq_no, symbol, price=0.0, size=0.0, direction=None, source_tier=1, quality_flags=0, version=2, arrival_mono=None, source="longport_ws", event_type="trade", priority=2))]
    pub fn new(seq_no:i64,symbol:String,price:f64,size:f64,direction:Option<String>,source_tier:i32,quality_flags:i32,version:i32,arrival_mono:Option<f64>,source:&str,event_type:&str,priority:i32)->Self{Self{seq_no,symbol,arrival_mono:arrival_mono.unwrap_or_else(now_secs),source:source.to_string(),event_type:event_type.to_string(),priority,price,size,direction,source_tier,quality_flags,version}}
}

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct DataQualityAlert {
    #[pyo3(get, set)] pub seq_no: i64,
    #[pyo3(get, set)] pub symbol: String,
    #[pyo3(get, set)] pub arrival_mono: f64,
    #[pyo3(get, set)] pub source: String,
    #[pyo3(get, set)] pub event_type: String,
    #[pyo3(get, set)] pub priority: i32,
    #[pyo3(get, set)] pub severity: String,
    #[pyo3(get, set)] pub reason: String,
    #[pyo3(get, set)] pub field_name: Option<String>,
    #[pyo3(get, set)] pub raw_value: Option<Py<PyAny>>,
    #[pyo3(get, set)] pub corrected_value: Option<Py<PyAny>>,
    #[pyo3(get, set)] pub context: Option<Py<PyDict>>,
}
#[pymethods]
impl DataQualityAlert {
    #[new]
    #[pyo3(signature = (seq_no, symbol, severity="info", reason="", field_name=None, raw_value=None, corrected_value=None, context=None, arrival_mono=None, source="longport_ws", event_type="system", priority=2))]
    pub fn new(seq_no:i64,symbol:String,severity:&str,reason:&str,field_name:Option<String>,raw_value:Option<Py<PyAny>>,corrected_value:Option<Py<PyAny>>,context:Option<Py<PyDict>>,arrival_mono:Option<f64>,source:&str,event_type:&str,priority:i32)->Self{Self{seq_no,symbol,arrival_mono:arrival_mono.unwrap_or_else(now_secs),source:source.to_string(),event_type:event_type.to_string(),priority: if severity=="error"||severity=="critical" {1} else {priority},severity:severity.to_string(),reason:reason.to_string(),field_name,raw_value,corrected_value,context}}
}

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct CircuitBreakerEvent {
    #[pyo3(get, set)] pub seq_no: i64,
    #[pyo3(get, set)] pub symbol: String,
    #[pyo3(get, set)] pub arrival_mono: f64,
    #[pyo3(get, set)] pub source: String,
    #[pyo3(get, set)] pub event_type: String,
    #[pyo3(get, set)] pub priority: i32,
    #[pyo3(get, set)] pub reason: String,
    #[pyo3(get, set)] pub z_score: Option<f64>,
    #[pyo3(get, set)] pub gap_seconds: Option<f64>,
    #[pyo3(get, set)] pub reset_after_seconds: f64,
    #[pyo3(get, set)] pub is_open: bool,
}
#[pymethods]
impl CircuitBreakerEvent {
    #[new]
    #[pyo3(signature = (seq_no, symbol, reason="tick_jump", z_score=None, gap_seconds=None, reset_after_seconds=5.0, is_open=true, arrival_mono=None, source="longport_ws", event_type="system", priority=0))]
    pub fn new(seq_no:i64,symbol:String,reason:&str,z_score:Option<f64>,gap_seconds:Option<f64>,reset_after_seconds:f64,is_open:bool,arrival_mono:Option<f64>,source:&str,event_type:&str,priority:i32)->Self{Self{seq_no,symbol,arrival_mono:arrival_mono.unwrap_or_else(now_secs),source:source.to_string(),event_type:event_type.to_string(),priority,reason:reason.to_string(),z_score,gap_seconds,reset_after_seconds,is_open}}
}

pub fn register(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<EventType>()?; m.add_class::<EventPriority>()?; m.add_class::<QualityFlag>()?;
    m.add_class::<AlertSeverity>()?; m.add_class::<BreakerReason>()?; m.add_class::<BaseEvent>()?;
    m.add_class::<L2Level>()?; m.add_class::<CleanQuoteEvent>()?; m.add_class::<CleanDepthEvent>()?;
    m.add_class::<CleanTradeEvent>()?; m.add_class::<DataQualityAlert>()?; m.add_class::<CircuitBreakerEvent>()?;
    let _ = py;
    Ok(())
}
