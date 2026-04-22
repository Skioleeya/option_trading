use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};
use std::collections::HashSet;

const CONTRACT_MULTIPLIER: f64 = 100.0;

#[derive(Default)]
struct SnapshotMetrics {
    net_delta_exposure_live: f64,
    net_gamma_exposure_live: f64,
    midpoint_tickrule_count: i64,
    condition_filtered_count: i64,
    complex_spread_count: i64,
    residual_delta_after_netting: f64,
    oi_participation_ratio_live: f64,
    flow_suppression_bias: f64,
    flow_dominance_ratio: f64,
    put_ask_side_volume: f64,
    call_bid_side_volume: f64,
    call_ask_side_volume: f64,
    put_bid_side_volume: f64,
}

pub fn condition_filtered_text(trade_type: Option<&str>) -> bool {
    let text = trade_type
        .unwrap_or("")
        .to_uppercase()
        .replace(' ', "");
    if text.is_empty() {
        return false;
    }
    let blocked = [
        "LATE",
        "LATEPRINT",
        "OUTOFSEQUENCE",
        "OUTOFSEQ",
        "AVERAGEPRICE",
        "AVGPRICE",
        "AVERAGE",
    ];
    blocked.iter().any(|pattern| text.contains(pattern))
}

fn py_to_f64(value: &Bound<'_, PyAny>) -> Option<f64> {
    if value.is_none() {
        return None;
    }
    if let Ok(num) = value.extract::<f64>() {
        return num.is_finite().then_some(num);
    }
    if let Ok(text) = value.extract::<String>()
        && let Ok(parsed) = text.trim().parse::<f64>()
    {
        return parsed.is_finite().then_some(parsed);
    }
    None
}

fn py_to_string(value: &Bound<'_, PyAny>) -> Option<String> {
    if value.is_none() {
        return None;
    }
    if let Ok(text) = value.extract::<String>() {
        let trimmed = text.trim();
        if !trimmed.is_empty() {
            return Some(trimmed.to_string());
        }
    }
    None
}

fn get_item_any<'py>(row: &Bound<'py, PyAny>, key: &str) -> Option<Bound<'py, PyAny>> {
    if let Ok(item) = row.get_item(key) {
        return Some(item);
    }
    row.getattr(key).ok()
}

fn row_f64(row: &Bound<'_, PyAny>, key: &str) -> Option<f64> {
    get_item_any(row, key).and_then(|value| py_to_f64(&value))
}

fn row_string(row: &Bound<'_, PyAny>, key: &str) -> Option<String> {
    get_item_any(row, key).and_then(|value| py_to_string(&value))
}

fn near_equal(left: f64, right: f64, epsilon: f64) -> bool {
    (left - right).abs() <= epsilon.abs().max(1e-6)
}

fn classify_direction(impact: f64, ask_volume: f64, bid_volume: f64) -> i64 {
    if impact > 1e-6 {
        return 1;
    }
    if impact < -1e-6 {
        return -1;
    }
    if ask_volume > bid_volume && ask_volume > 0.0 {
        return 1;
    }
    if bid_volume > ask_volume && bid_volume > 0.0 {
        return -1;
    }
    0
}

fn infer_is_call(row: &Bound<'_, PyAny>) -> Option<bool> {
    let opt_type = row_string(row, "opt_type")
        .or_else(|| row_string(row, "type"))
        .unwrap_or_default()
        .to_uppercase();
    if opt_type == "CALL" {
        return Some(true);
    }
    if opt_type == "PUT" {
        return Some(false);
    }
    if let Some(flag) = get_item_any(row, "is_call")
        && let Ok(value) = flag.extract::<bool>()
    {
        return Some(value);
    }
    None
}

fn push_snapshot_metrics(py: Python<'_>, metrics: SnapshotMetrics) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("net_delta_exposure_live", metrics.net_delta_exposure_live)?;
    out.set_item("net_gamma_exposure_live", metrics.net_gamma_exposure_live)?;
    out.set_item("midpoint_tickrule_count", metrics.midpoint_tickrule_count)?;
    out.set_item("condition_filtered_count", metrics.condition_filtered_count)?;
    out.set_item("complex_spread_count", metrics.complex_spread_count)?;
    out.set_item(
        "residual_delta_after_netting",
        metrics.residual_delta_after_netting,
    )?;
    out.set_item(
        "oi_participation_ratio_live",
        metrics.oi_participation_ratio_live,
    )?;
    out.set_item("flow_suppression_bias", metrics.flow_suppression_bias)?;
    out.set_item("flow_dominance_ratio", metrics.flow_dominance_ratio)?;
    out.set_item("put_ask_side_volume", metrics.put_ask_side_volume)?;
    out.set_item("call_bid_side_volume", metrics.call_bid_side_volume)?;
    out.set_item("call_ask_side_volume", metrics.call_ask_side_volume)?;
    out.set_item("put_bid_side_volume", metrics.put_bid_side_volume)?;
    Ok(out.into())
}

pub fn mm_snapshot_metrics_impl(
    py: Python<'_>,
    chain_rows: Option<&Bound<'_, PyAny>>,
    epsilon: f64,
    complex_delta_threshold: f64,
) -> PyResult<Py<PyDict>> {
    let mut metrics = SnapshotMetrics::default();
    let Some(rows_any) = chain_rows else {
        return push_snapshot_metrics(py, metrics);
    };

    let mut pos_delta_sum = 0.0;
    let mut neg_delta_sum = 0.0;
    let mut flow_size_sum = 0.0;
    let mut oi_weighted_sum = 0.0;
    let mut large_flow_strikes: HashSet<i64> = HashSet::new();

    let mut visit_row = |row: &Bound<'_, PyAny>| {
        let trade_type = row_string(row, "trade_type");
        let filtered = condition_filtered_text(trade_type.as_deref());
        if filtered {
            metrics.condition_filtered_count += 1;
        }

        let ask_volume = row_f64(row, "ask_volume").unwrap_or(0.0).max(0.0);
        let bid_volume = row_f64(row, "bid_volume").unwrap_or(0.0).max(0.0);
        let impact = row_f64(row, "impact_index").unwrap_or(0.0);
        let direction = classify_direction(impact, ask_volume, bid_volume);
        let size = if direction > 0 {
            ask_volume
        } else if direction < 0 {
            bid_volume
        } else {
            ask_volume.max(bid_volume)
        };

        let bid = row_f64(row, "bid");
        let ask = row_f64(row, "ask");
        let price = row_f64(row, "last_price");
        if let (Some(bid_px), Some(ask_px), Some(px)) = (bid, ask, price)
            && bid_px > 0.0
            && ask_px >= bid_px
            && px > 0.0
        {
            let mid = (bid_px + ask_px) * 0.5;
            if near_equal(px, mid, epsilon) {
                metrics.midpoint_tickrule_count += 1;
            }
        }

        let is_call = infer_is_call(row);
        if size > 0.0 {
            if is_call == Some(true) {
                if direction > 0 {
                    metrics.call_ask_side_volume += size;
                } else if direction < 0 {
                    metrics.call_bid_side_volume += size;
                }
            } else if is_call == Some(false) {
                if direction > 0 {
                    metrics.put_ask_side_volume += size;
                } else if direction < 0 {
                    metrics.put_bid_side_volume += size;
                }
            }
        }

        if filtered || direction == 0 || size <= 0.0 {
            return;
        }

        let delta = row_f64(row, "computed_delta")
            .or_else(|| row_f64(row, "delta"))
            .unwrap_or(0.0);
        let gamma = row_f64(row, "computed_gamma")
            .or_else(|| row_f64(row, "gamma"))
            .unwrap_or(0.0);
        let net_delta = (direction as f64) * size * CONTRACT_MULTIPLIER * delta;
        let net_gamma = size * CONTRACT_MULTIPLIER * gamma;
        metrics.net_delta_exposure_live += net_delta;
        metrics.net_gamma_exposure_live += net_gamma;

        if net_delta > 0.0 {
            pos_delta_sum += net_delta;
        } else if net_delta < 0.0 {
            neg_delta_sum += -net_delta;
        }
        if net_delta.abs() >= complex_delta_threshold {
            let strike = row_f64(row, "strike").unwrap_or(0.0);
            if strike > 0.0 {
                let strike_key = (strike * 100.0).round() as i64;
                large_flow_strikes.insert(strike_key);
            }
        }

        let oi = row_f64(row, "open_interest").unwrap_or(0.0);
        if oi > epsilon {
            flow_size_sum += size;
            oi_weighted_sum += size / oi.max(epsilon);
        }
    };

    if let Ok(iter) = rows_any.try_iter() {
        for item in iter.flatten() {
            visit_row(&item);
        }
    } else {
        return push_snapshot_metrics(py, metrics);
    }

    metrics.residual_delta_after_netting = if pos_delta_sum >= neg_delta_sum {
        pos_delta_sum - neg_delta_sum
    } else {
        -(neg_delta_sum - pos_delta_sum)
    };
    if pos_delta_sum > 0.0 && neg_delta_sum > 0.0 && large_flow_strikes.len() >= 2 {
        metrics.complex_spread_count = 1;
    }
    metrics.oi_participation_ratio_live = if flow_size_sum > 0.0 {
        oi_weighted_sum / flow_size_sum
    } else {
        0.0
    };

    let suppression = (metrics.put_ask_side_volume + metrics.call_bid_side_volume)
        - (metrics.call_ask_side_volume + metrics.put_bid_side_volume);
    metrics.flow_suppression_bias = suppression;
    let total_side_volume = metrics.put_ask_side_volume
        + metrics.call_bid_side_volume
        + metrics.call_ask_side_volume
        + metrics.put_bid_side_volume;
    metrics.flow_dominance_ratio = if total_side_volume > epsilon {
        suppression / total_side_volume
    } else {
        0.0
    };

    push_snapshot_metrics(py, metrics)
}
