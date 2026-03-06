use std::collections::HashMap;
use crate::schema::InstitutionalMarketEvent;

pub struct ThreatEngine {
    last_bid_vol: HashMap<String, u64>,
    last_ask_vol: HashMap<String, u64>,
    last_bid_price: HashMap<String, f64>,
    last_ask_price: HashMap<String, f64>,
}

impl ThreatEngine {
    pub fn new() -> Self {
        ThreatEngine {
            last_bid_vol: HashMap::new(),
            last_ask_vol: HashMap::new(),
            last_bid_price: HashMap::new(),
            last_ask_price: HashMap::new(),
        }
    }

    pub fn calculate_ofii(&mut self, symbol: &str, bid: f64, bid_vol: u64, ask: f64, ask_vol: u64) -> f64 {
        let prev_bid = *self.last_bid_price.get(symbol).unwrap_or(&0.0);
        let prev_bid_vol = *self.last_bid_vol.get(symbol).unwrap_or(&0);
        let prev_ask = *self.last_ask_price.get(symbol).unwrap_or(&0.0);
        let prev_ask_vol = *self.last_ask_vol.get(symbol).unwrap_or(&0);

        let d_bid = if bid > prev_bid {
            bid_vol as f64
        } else if bid == prev_bid {
            (bid_vol as i64 - prev_bid_vol as i64) as f64
        } else {
            -(prev_bid_vol as f64)
        };

        let d_ask = if ask < prev_ask {
            ask_vol as f64
        } else if ask == prev_ask {
            (ask_vol as i64 - prev_ask_vol as i64) as f64
        } else {
            -(prev_ask_vol as f64)
        };

        self.last_bid_price.insert(symbol.to_string(), bid);
        self.last_bid_vol.insert(symbol.to_string(), bid_vol);
        self.last_ask_price.insert(symbol.to_string(), ask);
        self.last_ask_vol.insert(symbol.to_string(), ask_vol);

        d_bid - d_ask
    }

    pub fn detect_sweep(&self, volume: u64, threshold: u64) -> bool {
        volume > threshold
    }
}
