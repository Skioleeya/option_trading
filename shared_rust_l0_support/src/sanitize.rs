use crate::events::{AlertSeverity, BreakerReason, CircuitBreakerEvent, CleanDepthEvent, CleanQuoteEvent, CleanTradeEvent, DataQualityAlert, L2Level, QualityFlag};
use crate::quality::DataQualityReport;
use pyo3::prelude::*;
use pyo3::types::PyAny;
use std::collections::{HashMap, VecDeque};
use std::time::{SystemTime, UNIX_EPOCH};

fn now_secs() -> f64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0)
}
fn safe_float(v: Option<&Bound<'_, PyAny>>, fallback: f64) -> (f64, bool) {
    let Some(v) = v else { return (fallback, false); };
    match v.extract::<f64>() { Ok(f) if f.is_finite() => (f, false), _ => (fallback, true) }
}
fn opt_float(v: Option<&Bound<'_, PyAny>>) -> Option<f64> { v.and_then(|x| x.extract::<f64>().ok()).filter(|x| x.is_finite()) }
fn parse_levels(raw: Option<&Bound<'_, PyAny>>) -> Vec<L2Level> {
    let Some(raw) = raw else { return Vec::new(); };
    let Ok(iter) = raw.try_iter() else { return Vec::new(); };
    let mut out = Vec::new();
    for item in iter.flatten() {
        let any = item.as_any();
        if let Ok(seq) = any.extract::<Vec<f64>>() {
            if seq.len() >= 2 && seq[0].is_finite() && seq[1].is_finite() && seq[1] > 0.0 {
                out.push(L2Level { price: seq[0], size: seq[1], order_count: 0 });
                continue;
            }
        }
        if let Ok(map) = any.extract::<HashMap<String, Py<PyAny>>>() {
            let price = map.get("price").and_then(|v| v.bind(any.py()).extract::<f64>().ok()).unwrap_or(0.0);
            let size = map.get("size").or_else(|| map.get("volume")).and_then(|v| v.bind(any.py()).extract::<f64>().ok()).unwrap_or(0.0);
            let count = map.get("order_count").and_then(|v| v.bind(any.py()).extract::<i64>().ok()).unwrap_or(0);
            if price.is_finite() && size.is_finite() && size > 0.0 {
                out.push(L2Level { price, size, order_count: count });
            }
        }
    }
    out
}
fn rolling_stats(window: &VecDeque<f64>) -> (f64, f64) {
    if window.is_empty() { return (0.0, 0.0); }
    let n = window.len() as f64;
    let mean = window.iter().sum::<f64>() / n;
    let var = window.iter().map(|x| (x - mean) * (x - mean)).sum::<f64>() / n;
    (mean, var.sqrt())
}
fn quantile(window: &VecDeque<f64>, q: f64) -> f64 {
    let mut v = window.iter().copied().collect::<Vec<_>>();
    v.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    if v.is_empty() { 0.0 } else { v[((q * v.len() as f64) as usize).min(v.len() - 1)] }
}

#[derive(Default, Clone)]
struct SymbolState { price_window: VecDeque<f64>, last_event_mono: f64, oi_deltas: VecDeque<f64>, last_oi: Option<f64>, breaker_open: bool, breaker_open_until: f64 }

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct StatisticalBreaker { #[pyo3(get)] tick_jump_sigma: f64, #[pyo3(get)] gap_threshold_s: f64, #[pyo3(get)] oi_quantile: f64, #[pyo3(get)] breaker_reset_s: f64, states: HashMap<String, SymbolState> }
#[pymethods]
impl StatisticalBreaker {
    #[new]
    #[pyo3(signature = (tick_jump_sigma=5.0, gap_threshold_s=3.0, oi_quantile=0.99, breaker_reset_s=5.0))]
    fn new(tick_jump_sigma: f64, gap_threshold_s: f64, oi_quantile: f64, breaker_reset_s: f64) -> Self { Self { tick_jump_sigma, gap_threshold_s, oi_quantile, breaker_reset_s, states: HashMap::new() } }
    #[pyo3(signature = (symbol, bid, ask, open_interest=None, seq_no=0))]
    fn check_quote(&mut self, py: Python<'_>, symbol: String, bid: f64, ask: f64, open_interest: Option<f64>, seq_no: i64) -> PyResult<(bool, Option<Py<CircuitBreakerEvent>>, Option<Py<DataQualityAlert>>)> {
        let now = now_secs();
        let state = self.states.entry(symbol.clone()).or_insert_with(|| SymbolState { last_event_mono: now, ..Default::default() });
        if state.breaker_open {
            if now < state.breaker_open_until { return Ok((false, None, None)); }
            state.breaker_open = false;
            let ev = Py::new(py, CircuitBreakerEvent::new(seq_no, symbol, BreakerReason::TICK_JUMP, None, None, self.breaker_reset_s, false, Some(now), "longport_ws", "system", 0))?;
            return Ok((true, Some(ev), None));
        }
        if bid.is_finite() && ask.is_finite() && bid > ask {
            let alert = Py::new(py, DataQualityAlert::new(seq_no, symbol, AlertSeverity::WARNING, BreakerReason::BID_GT_ASK, Some("bid/ask".to_string()), None, None, None, Some(now), "longport_ws", "system", 2))?;
            return Ok((true, None, Some(alert)));
        }
        let gap_s = now - state.last_event_mono;
        state.last_event_mono = now;
        let gap_alert = if gap_s > self.gap_threshold_s {
            let ctx = pyo3::types::PyDict::new(py); ctx.set_item("gap_seconds", gap_s)?;
            Some(Py::new(py, DataQualityAlert::new(seq_no, symbol.clone(), AlertSeverity::WARNING, BreakerReason::GAP_TIMEOUT, None, None, None, Some(ctx.unbind()), Some(now), "longport_ws", "system", 2))?)
        } else { None };
        let mid = if bid.is_finite() && ask.is_finite() { Some((bid + ask) / 2.0) } else { None };
        if let Some(mid) = mid {
            if state.price_window.len() >= 10 {
                let (mean, std) = rolling_stats(&state.price_window);
                if std > 0.0 {
                    let z = (mid - mean).abs() / std;
                    if z > self.tick_jump_sigma {
                        state.breaker_open = true;
                        state.breaker_open_until = now + self.breaker_reset_s;
                        let ev = Py::new(py, CircuitBreakerEvent::new(seq_no, symbol.clone(), BreakerReason::TICK_JUMP, Some(z), None, self.breaker_reset_s, true, Some(now), "longport_ws", "system", 0))?;
                        return Ok((false, Some(ev), gap_alert));
                    }
                }
            }
            if state.price_window.len() == 50 { state.price_window.pop_front(); }
            state.price_window.push_back(mid);
        }
        let mut oi_alert = None;
        if let Some(oi) = open_interest.filter(|x| x.is_finite()) {
            if let Some(last_oi) = state.last_oi {
                let delta = (oi - last_oi).abs();
                if state.oi_deltas.len() >= 20 {
                    let q99 = quantile(&state.oi_deltas, self.oi_quantile);
                    if delta > q99 && q99 > 0.0 {
                        let ctx = pyo3::types::PyDict::new(py); ctx.set_item("oi_delta", delta)?; ctx.set_item("q99", q99)?;
                        oi_alert = Some(Py::new(py, DataQualityAlert::new(seq_no, symbol.clone(), AlertSeverity::INFO, BreakerReason::OI_SURGE, None, None, None, Some(ctx.unbind()), Some(now), "longport_ws", "system", 2))?);
                    }
                }
                if state.oi_deltas.len() == 200 { state.oi_deltas.pop_front(); }
                state.oi_deltas.push_back(delta);
            }
            state.last_oi = Some(oi);
        }
        Ok((true, None, gap_alert.or(oi_alert)))
    }
    fn reset_symbol(&mut self, symbol: String) { self.states.remove(&symbol); }
    fn reset_all(&mut self) { self.states.clear(); }
}

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct SanitizePipelineV2 { breaker: Option<StatisticalBreaker> }
#[pymethods]
impl SanitizePipelineV2 {
    #[new]
    #[pyo3(signature = (enable_statistical_check=true, tick_jump_sigma=5.0, gap_threshold_s=3.0, oi_quantile=0.99, breaker_reset_s=5.0))]
    fn new(enable_statistical_check: bool, tick_jump_sigma: f64, gap_threshold_s: f64, oi_quantile: f64, breaker_reset_s: f64) -> Self {
        let breaker = enable_statistical_check.then(|| StatisticalBreaker::new(tick_jump_sigma, gap_threshold_s, oi_quantile, breaker_reset_s));
        Self { breaker }
    }
    fn parse_quote(&mut self, py: Python<'_>, raw: &Bound<'_, PyAny>) -> PyResult<Option<Py<CleanQuoteEvent>>> { let (ev, _) = self.parse_with_quality(py, raw, "quote")?; Ok(ev.and_then(|o| o.extract(py).ok())) }
    fn parse_depth(&mut self, py: Python<'_>, raw: &Bound<'_, PyAny>) -> PyResult<Option<Py<CleanDepthEvent>>> { let (ev, _) = self.parse_with_quality(py, raw, "depth")?; Ok(ev.and_then(|o| o.extract(py).ok())) }
    fn parse_trade(&mut self, py: Python<'_>, raw: &Bound<'_, PyAny>) -> PyResult<Option<Py<CleanTradeEvent>>> { let (ev, _) = self.parse_with_quality(py, raw, "trade")?; Ok(ev.and_then(|o| o.extract(py).ok())) }
    #[pyo3(signature = (raw, event_hint="quote"))]
    fn parse_with_quality(&mut self, py: Python<'_>, raw: &Bound<'_, PyAny>, event_hint: &str) -> PyResult<(Option<Py<PyAny>>, DataQualityReport)> {
        let raw_dict = raw.extract::<HashMap<String, Py<PyAny>>>()?;
        match event_hint {
            "quote" => self.parse_quote_v2(py, &raw_dict),
            "depth" => self.parse_depth_v2(py, &raw_dict),
            "trade" => self.parse_trade_v2(py, &raw_dict),
            _ => { let mut report = DataQualityReport::new(raw_dict.get("symbol").and_then(|v| v.bind(py).extract::<String>().ok()).unwrap_or_default(), false, None, None, None, None); report.add_error(format!("Unknown event_hint: {}", event_hint)); Ok((None, report)) }
        }
    }
}
impl SanitizePipelineV2 {
    fn parse_quote_v2(&mut self, py: Python<'_>, raw: &HashMap<String, Py<PyAny>>) -> PyResult<(Option<Py<PyAny>>, DataQualityReport)> {
        let symbol = raw.get("symbol").and_then(|v| v.bind(py).extract::<String>().ok()).unwrap_or_else(|| "UNKNOWN".to_string());
        let seq_no = raw.get("seq_no").and_then(|v| v.bind(py).extract::<i64>().ok()).unwrap_or(0);
        let mut report = DataQualityReport::new(symbol.clone(), false, None, None, None, None);
        let mut flags = QualityFlag::OK;
        let (mut bid, c1) = safe_float(raw.get("bid").map(|x| x.bind(py)), 0.0); if c1 { flags |= QualityFlag::NAN_CLEANED; report.add_warning("bid NaN/Inf → 0".to_string()); }
        let (mut ask, c2) = safe_float(raw.get("ask").map(|x| x.bind(py)), 0.0); if c2 { flags |= QualityFlag::NAN_CLEANED; report.add_warning("ask NaN/Inf → 0".to_string()); }
        let (last, _) = safe_float(raw.get("last").map(|x| x.bind(py)), 0.0);
        let (volume, _) = safe_float(raw.get("volume").map(|x| x.bind(py)), 0.0);
        let (oi, _) = safe_float(raw.get("open_interest").map(|x| x.bind(py)), 0.0);
        if bid > ask && ask > 0.0 { flags |= QualityFlag::BID_GT_ASK; std::mem::swap(&mut bid, &mut ask); report.add_warning("bid>ask swapped".to_string()); }
        let mut delta = opt_float(raw.get("delta").map(|x| x.bind(py))); if raw.contains_key("delta") && delta.is_none() { flags |= QualityFlag::NAN_CLEANED; report.add_warning("delta NaN/Inf → None".to_string()); }
        let mut gamma = opt_float(raw.get("gamma").map(|x| x.bind(py))); if raw.contains_key("gamma") && gamma.is_none() { flags |= QualityFlag::NAN_CLEANED; report.add_warning("gamma NaN/Inf → None".to_string()); }
        let mut theta = opt_float(raw.get("theta").map(|x| x.bind(py))); if raw.contains_key("theta") && theta.is_none() { flags |= QualityFlag::NAN_CLEANED; report.add_warning("theta NaN/Inf → None".to_string()); }
        let mut vega = opt_float(raw.get("vega").map(|x| x.bind(py))); if raw.contains_key("vega") && vega.is_none() { flags |= QualityFlag::NAN_CLEANED; report.add_warning("vega NaN/Inf → None".to_string()); }
        let mut iv = opt_float(raw.get("iv").map(|x| x.bind(py))); if raw.contains_key("iv") && iv.is_none() { flags |= QualityFlag::NAN_CLEANED; report.add_warning("iv NaN/Inf → None".to_string()); }
        if let Some(breaker) = &mut self.breaker { let (passed, breaker_ev, stat_alert) = breaker.check_quote(py, symbol.clone(), bid, ask, Some(oi), seq_no)?; if let Some(alert) = stat_alert { report.add_warning(alert.bind(py).getattr("reason")?.extract::<String>()?); } if let Some(ev) = breaker_ev { if ev.bind(py).getattr("is_open")?.extract::<bool>()? { report.add_error(format!("Circuit breaker: {}", ev.bind(py).getattr("reason")?.extract::<String>()?)); return Ok((None, report)); } } if !passed { return Ok((None, report)); } }
        report.passed = true;
        let event = CleanQuoteEvent::new(seq_no, symbol, bid, ask, last, volume, oi, delta.take(), gamma.take(), theta.take(), vega.take(), iv.take(), opt_float(raw.get("strike").map(|x| x.bind(py))), raw.get("expiry").and_then(|v| v.bind(py).extract::<String>().ok()), raw.get("option_type").and_then(|v| v.bind(py).extract::<String>().ok()), 1, flags, 2, None, "longport_ws", "quote", 2);
        Ok((Some(Py::new(py, event)?.into_any()), report))
    }
    fn parse_depth_v2(&mut self, py: Python<'_>, raw: &HashMap<String, Py<PyAny>>) -> PyResult<(Option<Py<PyAny>>, DataQualityReport)> {
        let symbol = raw.get("symbol").and_then(|v| v.bind(py).extract::<String>().ok()).unwrap_or_else(|| "UNKNOWN".to_string());
        let seq_no = raw.get("seq_no").and_then(|v| v.bind(py).extract::<i64>().ok()).unwrap_or(0);
        let report = DataQualityReport::new(symbol.clone(), true, None, None, None, None);
        let bids = parse_levels(raw.get("bids").map(|x| x.bind(py))); let asks = parse_levels(raw.get("asks").map(|x| x.bind(py)));
        let (bid, c1) = safe_float(raw.get("bid").map(|x| x.bind(py)), 0.0); let (ask, c2) = safe_float(raw.get("ask").map(|x| x.bind(py)), 0.0);
        let flags = if c1 || c2 { QualityFlag::NAN_CLEANED } else { QualityFlag::OK };
        let ev = CleanDepthEvent::new(seq_no, symbol, Some(bids), Some(asks), if bid == 0.0 { None } else { Some(bid) }, if ask == 0.0 { None } else { Some(ask) }, opt_float(raw.get("bid_size").map(|x| x.bind(py))), opt_float(raw.get("ask_size").map(|x| x.bind(py))), 1, flags, 2, None, "longport_ws", "depth", 2);
        Ok((Some(Py::new(py, ev)?.into_any()), report))
    }
    fn parse_trade_v2(&mut self, py: Python<'_>, raw: &HashMap<String, Py<PyAny>>) -> PyResult<(Option<Py<PyAny>>, DataQualityReport)> {
        let symbol = raw.get("symbol").and_then(|v| v.bind(py).extract::<String>().ok()).unwrap_or_else(|| "UNKNOWN".to_string());
        let seq_no = raw.get("seq_no").and_then(|v| v.bind(py).extract::<i64>().ok()).unwrap_or(0);
        let mut report = DataQualityReport::new(symbol.clone(), false, None, None, None, None);
        let (price, cleaned) = safe_float(raw.get("price").map(|x| x.bind(py)), 0.0); if cleaned { report.add_error("price NaN/Inf — trade dropped".to_string()); return Ok((None, report)); }
        let (size, _) = safe_float(raw.get("size").or_else(|| raw.get("volume")).map(|x| x.bind(py)), 0.0);
        let direction = raw.get("direction").and_then(|v| v.bind(py).extract::<String>().ok());
        report.passed = true;
        let ev = CleanTradeEvent::new(seq_no, symbol, price, size, direction, 1, QualityFlag::OK, 2, None, "longport_ws", "trade", 2);
        Ok((Some(Py::new(py, ev)?.into_any()), report))
    }
}

pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<StatisticalBreaker>()?;
    m.add_class::<SanitizePipelineV2>()?;
    Ok(())
}
