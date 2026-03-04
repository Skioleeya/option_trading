use pyo3::prelude::*;

/// Kernel for VPIN v2 calculation. Processes a batch of trades and updates current bucket state.
///
/// Returns a tuple: (new_buy_vol, new_sell_vol, new_total_vol, completed_scores)
/// where completed_scores is a Vec<f64> of VPIN scores for any buckets completed during this batch.
#[pyfunction]
fn update_vpin_v2(
    mut buy_vol: f64,
    mut sell_vol: f64,
    mut total_vol: f64,
    bucket_size: f64,
    trades: Vec<(f64, f64)>, // (volume, dir_sign)
) -> PyResult<(f64, f64, f64, Vec<f64>)> {
    let mut completed_scores = Vec::with_capacity(32);
    
    for (vol, dir_sign) in trades {
        if vol <= 0.0 {
            continue;
        }
        
        let buy_v = if dir_sign > 0.0 { vol } else { 0.0 };
        let sell_v = if dir_sign < 0.0 { vol } else { 0.0 };
        
        buy_vol += buy_v;
        sell_vol += sell_v;
        total_vol += vol;
        
        while total_vol >= bucket_size {
            let score = if total_vol > 0.0 {
                (buy_vol - sell_vol).abs() / total_vol
            } else {
                0.0
            };
            completed_scores.push(score);
            
            let excess = total_vol - bucket_size;
            let fraction = if vol > 1e-9 { excess / vol } else { 0.0 };
            
            total_vol = excess;
            buy_vol = buy_v * fraction;
            sell_vol = sell_v * fraction;
        }
    }
    
    Ok((buy_vol, sell_vol, total_vol, completed_scores))
}

/// Kernel for BBO Imbalance v2 calculation. 
/// Computes top-levels weighted bid/ask imbalance.
#[pyfunction]
fn compute_bbo_weighted(
    bids: Vec<f64>,
    asks: Vec<f64>,
    max_levels: usize,
) -> PyResult<f64> {
    // Top 5 pre-calculated weights: 1.0, 0.5, 0.333, 0.25, 0.20
    let weights = [1.0, 0.5, 0.3333333333333333, 0.25, 0.20];
    
    let n = bids.len().min(asks.len()).min(max_levels).min(weights.len());
    if n == 0 {
        return Ok(0.0);
    }
    
    let mut w_bid = 0.0;
    let mut w_ask = 0.0;
    
    // Explicit loop helps LLVM unroll and auto-vectorize 
    for i in 0..n {
        let w = weights[i];
        let bid_vol = if bids[i] > 0.0 { bids[i] } else { 0.0 };
        let ask_vol = if asks[i] > 0.0 { asks[i] } else { 0.0 };
        w_bid += w * bid_vol;
        w_ask += w * ask_vol;
    }
    
    let total = w_bid + w_ask;
    if total <= 0.0 {
        return Ok(0.0);
    }
    
    Ok((w_bid - w_ask) / total)
}

/// A Python module implemented in Rust.
#[pymodule]
fn l1_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(update_vpin_v2, m)?)?;
    m.add_function(wrap_pyfunction!(compute_bbo_weighted, m)?)?;
    Ok(())
}
