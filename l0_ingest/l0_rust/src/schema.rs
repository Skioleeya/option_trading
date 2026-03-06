use serde::{Deserialize, Serialize};
use arrow::datatypes::{DataType, Field, Schema};
use std::sync::Arc;

#[derive(Debug, Clone, Serialize, Deserialize, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
#[repr(C)]
pub struct InstitutionalMarketEvent {
    pub symbol: [u8; 32],
    pub seq_no: u64,
    pub event_type: u8, // 1: Quote, 2: Depth, 3: Trade
    pub bid: f64,
    pub ask: f64,
    pub last_price: f64,
    pub spot: f64,
    pub volume: u64,
    pub open_interest: u64,
    pub implied_volatility: f64,
    pub impact_index: f64,   // Absolute Threat (OFII)
    pub is_sweep: bool,      // Institutional Sweep Flag
    pub ttm_seconds: f64,    // High-precision time decay
    pub arrival_mono_ns: u64,
    pub sequence_id: i64,    // For ordering
}

lazy_static::lazy_static! {
    pub static ref MARKET_EVENT_SCHEMA: Arc<Schema> = Arc::new(Schema::new(vec![
        Field::new("symbol", DataType::Utf8, false),
        Field::new("seq_no", DataType::UInt64, false),
        Field::new("event_type", DataType::UInt8, false),
        Field::new("bid", DataType::Float64, true),
        Field::new("ask", DataType::Float64, true),
        Field::new("last_price", DataType::Float64, true),
        Field::new("spot", DataType::Float64, true),
        Field::new("volume", DataType::UInt64, true),
        Field::new("open_interest", DataType::UInt64, true),
        Field::new("implied_volatility", DataType::Float64, true),
        Field::new("impact_index", DataType::Float64, true),
        Field::new("is_sweep", DataType::Boolean, false),
        Field::new("ttm_seconds", DataType::Float64, true),
        Field::new("arrival_mono_ns", DataType::UInt64, false),
        Field::new("sequence_id", DataType::Int64, false),
    ]));
}
