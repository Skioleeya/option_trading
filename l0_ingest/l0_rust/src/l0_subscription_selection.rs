use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};
use std::collections::{HashMap, HashSet};

const TOP_OI_SENTINELS: usize = 20;
const FLOW_SENTINELS: usize = 20;
const NEAR_SPOT_SENTINEL_STEPS: usize = 5;

#[derive(Clone)]
struct OptionLeg {
    symbol: String,
    strike: f64,
    side: char,
}

#[derive(Copy, Clone)]
struct CoreRange {
    low: f64,
    high: f64,
    left_idx: usize,
    right_idx: usize,
}

fn attr_or_item<'py>(obj: &Bound<'py, PyAny>, name: &str) -> Option<Bound<'py, PyAny>> {
    if let Ok(value) = obj.call_method1("get", (name,)) {
        if !value.is_none() {
            return Some(value);
        }
    }
    obj.getattr(name).ok().filter(|value| !value.is_none())
}

fn as_text(value: Option<Bound<'_, PyAny>>) -> Option<String> {
    value.and_then(|inner| inner.extract::<String>().ok())
}

fn as_float(value: Option<Bound<'_, PyAny>>) -> Option<f64> {
    let inner = value?;
    if let Ok(parsed) = inner.extract::<f64>() {
        return parsed.is_finite().then_some(parsed);
    }
    if let Ok(raw) = inner.extract::<String>() {
        return raw.parse::<f64>().ok().filter(|num| num.is_finite());
    }
    None
}

fn option_side_from_symbol(symbol: &str) -> Option<char> {
    let bytes = symbol.as_bytes();
    for idx in 0..bytes.len().saturating_sub(7) {
        let digits = &symbol[idx..idx + 6];
        let cp = bytes[idx + 6] as char;
        if digits.bytes().all(|byte| byte.is_ascii_digit()) && matches!(cp, 'C' | 'P') {
            return Some(cp);
        }
    }
    None
}

pub(crate) fn parse_symbol_expiry(symbol: &str) -> i64 {
    let bytes = symbol.as_bytes();
    let mut idx = 0usize;
    while idx < bytes.len() {
        if !bytes[idx].is_ascii_uppercase() {
            idx += 1;
            continue;
        }
        let start = idx;
        while idx < bytes.len() && bytes[idx].is_ascii_uppercase() {
            idx += 1;
        }
        if start == 0 && idx + 7 <= bytes.len() {
            let digits = &symbol[idx..idx + 6];
            let cp = bytes[idx + 6];
            if digits.bytes().all(|byte| byte.is_ascii_digit()) && matches!(cp, b'C' | b'P') {
                return digits.parse::<i64>().unwrap_or(999_999);
            }
        }
    }
    999_999
}

pub(crate) fn symbol_priority_key(
    symbol: &str,
    spot: Option<f64>,
    strike_map: &HashMap<String, f64>,
    symbol_priority: &HashMap<String, i64>,
) -> (i64, i64, f64, String) {
    let distance = match (spot, strike_map.get(symbol)) {
        (Some(spot_value), Some(strike)) => (strike - spot_value).abs(),
        _ => f64::INFINITY,
    };
    let priority = *symbol_priority.get(symbol).unwrap_or(&9);
    (
        priority,
        parse_symbol_expiry(symbol),
        distance,
        symbol.to_string(),
    )
}

fn add_symbol(
    symbols: &mut HashSet<String>,
    priority: &mut HashMap<String, i64>,
    symbol: &str,
    rank: i64,
) {
    symbols.insert(symbol.to_string());
    let entry = priority.entry(symbol.to_string()).or_insert(rank);
    if rank < *entry {
        *entry = rank;
    }
}

fn collect_legs(rows: &Bound<'_, PyAny>) -> PyResult<(Vec<f64>, Vec<OptionLeg>)> {
    let mut strikes = Vec::new();
    let mut legs = Vec::new();
    for item in rows.try_iter()? {
        let row = item?;
        let strike = as_float(attr_or_item(&row, "price")).unwrap_or(0.0);
        if !strike.is_finite() || strike <= 0.0 {
            continue;
        }
        strikes.push(strike);
        if let Some(symbol) = as_text(attr_or_item(&row, "call_symbol")) {
            legs.push(OptionLeg {
                symbol,
                strike,
                side: 'C',
            });
        }
        if let Some(symbol) = as_text(attr_or_item(&row, "put_symbol")) {
            legs.push(OptionLeg {
                symbol,
                strike,
                side: 'P',
            });
        }
    }
    strikes.sort_by(|left, right| left.partial_cmp(right).unwrap_or(std::cmp::Ordering::Equal));
    strikes.dedup_by(|left, right| (*left - *right).abs() < f64::EPSILON);
    Ok((strikes, legs))
}

fn nearest_index(strikes: &[f64], spot: f64) -> Option<usize> {
    strikes
        .iter()
        .enumerate()
        .min_by(|(_, left), (_, right)| {
            (*left - spot)
                .abs()
                .partial_cmp(&(*right - spot).abs())
                .unwrap_or(std::cmp::Ordering::Equal)
        })
        .map(|(idx, _)| idx)
}

fn initial_range(strikes: &[f64], spot: f64, steps: usize) -> Option<CoreRange> {
    let center = nearest_index(strikes, spot)?;
    let left = center.saturating_sub(steps);
    let right = (center + steps).min(strikes.len().saturating_sub(1));
    Some(CoreRange {
        low: strikes[left],
        high: strikes[right],
        left_idx: left,
        right_idx: right,
    })
}

fn dynamic_raw_range(points: &[(f64, f64)], coverage: f64) -> Option<(f64, f64)> {
    let total: f64 = points.iter().map(|(_, volume)| *volume).sum();
    if total <= 0.0 {
        return None;
    }
    let target = total * coverage.clamp(0.01, 1.0);
    let (mut best_left, mut best_right, mut best_width) = (0usize, points.len() - 1, f64::INFINITY);
    let (mut left, mut running) = (0usize, 0.0);
    for right in 0..points.len() {
        running += points[right].1;
        while left <= right && running - points[left].1 >= target {
            running -= points[left].1;
            left += 1;
        }
        if running >= target {
            let width = points[right].0 - points[left].0;
            if width < best_width {
                best_left = left;
                best_right = right;
                best_width = width;
            }
        }
    }
    best_width
        .is_finite()
        .then_some((points[best_left].0, points[best_right].0))
}

fn expand_range(strikes: &[f64], raw: (f64, f64), buffer: usize) -> CoreRange {
    let left_idx = strikes
        .iter()
        .position(|strike| *strike >= raw.0)
        .unwrap_or(0);
    let right_idx = strikes
        .iter()
        .rposition(|strike| *strike <= raw.1)
        .unwrap_or(strikes.len().saturating_sub(1));
    let left = left_idx.saturating_sub(buffer);
    let right = (right_idx + buffer).min(strikes.len().saturating_sub(1));
    CoreRange {
        low: strikes[left],
        high: strikes[right],
        left_idx: left,
        right_idx: right,
    }
}

fn positive_field(row: &Bound<'_, PyAny>, name: &str) -> f64 {
    as_float(attr_or_item(row, name))
        .filter(|num| *num > 0.0)
        .unwrap_or(0.0)
}

fn collect_snapshot_maps(
    snapshot: &Bound<'_, PyAny>,
) -> PyResult<(
    HashMap<String, (char, f64, f64)>,
    Vec<(String, f64, f64, f64)>,
)> {
    let mut volumes = HashMap::new();
    let mut sentinels = Vec::new();
    for item in snapshot.try_iter()? {
        let row = item?;
        let Some(symbol) = as_text(attr_or_item(&row, "symbol")) else {
            continue;
        };
        let side = as_text(attr_or_item(&row, "opt_type"))
            .and_then(|text| text.chars().next())
            .or_else(|| option_side_from_symbol(&symbol));
        let Some(side) = side.filter(|ch| matches!(ch, 'C' | 'P')) else {
            continue;
        };
        let strike = as_float(attr_or_item(&row, "strike")).unwrap_or(0.0);
        if !strike.is_finite() || strike <= 0.0 {
            continue;
        }
        let volume = positive_field(&row, "volume");
        let current_volume = positive_field(&row, "current_volume");
        let open_interest = positive_field(&row, "open_interest");
        if volume > 0.0 {
            volumes
                .entry(symbol.clone())
                .and_modify(|(_, _, old)| *old += volume)
                .or_insert((side, strike, volume));
        }
        sentinels.push((symbol, strike, open_interest, volume + current_volume));
    }
    Ok((volumes, sentinels))
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn select_targets_impl(
    py: Python<'_>,
    rows: Bound<'_, PyAny>,
    chain_snapshot: Bound<'_, PyAny>,
    spot: f64,
    first_source_seen_at_mono: Option<f64>,
    now_mono: f64,
    initial_steps: usize,
    dynamic_after_sec: f64,
    coverage: f64,
    core_buffer_steps: usize,
) -> PyResult<Py<PyDict>> {
    let (strikes, legs) = collect_legs(&rows)?;
    let (volumes, sentinel_rows) = collect_snapshot_maps(&chain_snapshot)?;
    let mut priority = HashMap::new();
    let mut core = HashSet::new();
    let mut sentinels = HashSet::new();
    let base_range = initial_range(&strikes, spot, initial_steps).unwrap_or(CoreRange {
        low: spot,
        high: spot,
        left_idx: 0,
        right_idx: 0,
    });
    let dynamic_ready = first_source_seen_at_mono
        .map(|start| now_mono - start >= dynamic_after_sec)
        .unwrap_or(false);
    let mut raw_call = None;
    let mut raw_put = None;
    let mut call_range = Some(base_range);
    let mut put_range = Some(base_range);
    let (mut call_phase, mut put_phase) = ("initial", "initial");
    if dynamic_ready {
        call_phase = "dynamic_guard_initial";
        put_phase = "dynamic_guard_initial";
        let mut call_points = Vec::new();
        let mut put_points = Vec::new();
        for (_, (side, strike, volume)) in volumes {
            if side == 'C' {
                call_points.push((strike, volume));
            } else {
                put_points.push((strike, volume));
            }
        }
        call_points.sort_by(|left, right| {
            left.0
                .partial_cmp(&right.0)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        put_points.sort_by(|left, right| {
            left.0
                .partial_cmp(&right.0)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        raw_call = dynamic_raw_range(&call_points, coverage);
        raw_put = dynamic_raw_range(&put_points, coverage);
        if let Some(raw) = raw_call {
            call_range = Some(expand_range(&strikes, raw, core_buffer_steps));
            call_phase = "dynamic";
        }
        if let Some(raw) = raw_put {
            put_range = Some(expand_range(&strikes, raw, core_buffer_steps));
            put_phase = "dynamic";
        }
    }
    for leg in &legs {
        let range = if leg.side == 'C' {
            call_range
        } else {
            put_range
        };
        if let Some(core_range) = range {
            if leg.strike >= core_range.low && leg.strike <= core_range.high {
                add_symbol(&mut core, &mut priority, &leg.symbol, 2);
            }
        }
    }
    if let Some(center) = nearest_index(&strikes, spot) {
        let left = center.saturating_sub(NEAR_SPOT_SENTINEL_STEPS);
        let right = (center + NEAR_SPOT_SENTINEL_STEPS).min(strikes.len().saturating_sub(1));
        for leg in &legs {
            if leg.strike >= strikes[left] && leg.strike <= strikes[right] {
                add_symbol(&mut sentinels, &mut priority, &leg.symbol, 1);
            }
        }
    }
    let mut by_oi = sentinel_rows.clone();
    by_oi.sort_by(|left, right| {
        right
            .2
            .partial_cmp(&left.2)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    for (symbol, _, _, _) in by_oi
        .into_iter()
        .filter(|row| row.2 > 0.0)
        .take(TOP_OI_SENTINELS)
    {
        add_symbol(&mut sentinels, &mut priority, &symbol, 2);
    }
    let mut by_flow = sentinel_rows;
    by_flow.sort_by(|left, right| {
        right
            .3
            .partial_cmp(&left.3)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    for (symbol, _, _, _) in by_flow
        .into_iter()
        .filter(|row| row.3 > 0.0)
        .take(FLOW_SENTINELS)
    {
        add_symbol(&mut sentinels, &mut priority, &symbol, 3);
    }
    let sentinel_count = sentinels.len();
    let mut targets = core.clone();
    targets.extend(sentinels.iter().cloned());
    let strike_map = PyDict::new(py);
    for leg in &legs {
        if targets.contains(&leg.symbol) {
            strike_map.set_item(&leg.symbol, leg.strike)?;
        }
    }
    let out = PyDict::new(py);
    out.set_item("targets", targets.into_iter().collect::<Vec<_>>())?;
    out.set_item("core_targets", core.into_iter().collect::<Vec<_>>())?;
    out.set_item("sentinel_targets", sentinels.into_iter().collect::<Vec<_>>())?;
    out.set_item("symbol_to_strike", strike_map)?;
    out.set_item("priority_by_symbol", priority)?;
    out.set_item("phase", if dynamic_ready { "dynamic" } else { "initial" })?;
    out.set_item("call_phase", call_phase)?;
    out.set_item("put_phase", put_phase)?;
    out.set_item("call_core_range", call_range.map(|range| (range.low, range.high)))?;
    out.set_item("put_core_range", put_range.map(|range| (range.low, range.high)))?;
    out.set_item("call_core_step_range", call_range.map(|range| (range.left_idx, range.right_idx)))?;
    out.set_item("put_core_step_range", put_range.map(|range| (range.left_idx, range.right_idx)))?;
    out.set_item("call_raw_range", raw_call)?;
    out.set_item("put_raw_range", raw_put)?;
    out.set_item("sentinel_count", sentinel_count)?;
    Ok(out.unbind())
}
