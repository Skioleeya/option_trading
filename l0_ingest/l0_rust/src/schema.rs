use arrow::datatypes::{DataType, Field, Schema};
use serde::{Deserialize, Serialize};
use std::sync::Arc;

pub const SHM_META_MAGIC: u32 = 0x4C305348; // "L0SH"
pub const SHM_SCHEMA_VERSION_V1: u32 = 1;
pub const SHM_SCHEMA_VERSION_V2: u32 = 2;
pub const SHM_SCHEMA_VERSION: u32 = SHM_SCHEMA_VERSION_V2;

#[derive(Debug, Clone, Serialize, Deserialize, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
#[repr(C)]
pub struct InstitutionalMarketEvent {
    pub symbol: [u8; 32],
    pub seq_no: u64,
    pub event_type: u8, // 1: Quote, 2: Depth, 3: Trade
    pub trade_type: [u8; 16],
    pub trade_session: [u8; 16],
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
    pub current_volume: u64,
    pub turnover: f64,
    pub current_turnover: f64,
}

#[derive(Debug, Clone)]
pub struct ArrowMarketEvent {
    pub symbol: String,
    pub seq_no: u64,
    pub event_type: u8,
    pub trade_type: Option<String>,
    pub trade_session: Option<String>,
    pub bid: Option<f64>,
    pub ask: Option<f64>,
    pub last_price: Option<f64>,
    pub volume: Option<u64>,
    pub bid_volume: Option<u64>,
    pub ask_volume: Option<u64>,
    pub current_volume: Option<u64>,
    pub turnover: Option<f64>,
    pub current_turnover: Option<f64>,
    pub impact_index: Option<f64>,
    pub is_sweep: bool,
    pub arrival_mono_ns: u64,
}

lazy_static::lazy_static! {
    pub static ref MARKET_EVENT_SCHEMA: Arc<Schema> = Arc::new(Schema::new(vec![
        Field::new("symbol", DataType::Utf8, false),
        Field::new("seq_no", DataType::UInt64, false),
        Field::new("event_type", DataType::UInt8, false),
        Field::new("trade_type", DataType::Utf8, true),
        Field::new("trade_session", DataType::Utf8, true),
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
        Field::new("current_volume", DataType::UInt64, true),
        Field::new("turnover", DataType::Float64, true),
        Field::new("current_turnover", DataType::Float64, true),
    ]));
    pub static ref ARROW_IPC_SCHEMA: Arc<Schema> = Arc::new(Schema::new(vec![
        Field::new("symbol", DataType::Utf8, false),
        Field::new("seq_no", DataType::UInt64, false),
        Field::new("event_type", DataType::UInt8, false),
        Field::new("trade_type", DataType::Utf8, true),
        Field::new("trade_session", DataType::Utf8, true),
        Field::new("bid", DataType::Float64, true),
        Field::new("ask", DataType::Float64, true),
        Field::new("last_price", DataType::Float64, true),
        Field::new("volume", DataType::UInt64, true),
        Field::new("bid_volume", DataType::UInt64, true),
        Field::new("ask_volume", DataType::UInt64, true),
        Field::new("current_volume", DataType::UInt64, true),
        Field::new("turnover", DataType::Float64, true),
        Field::new("current_turnover", DataType::Float64, true),
        Field::new("impact_index", DataType::Float64, true),
        Field::new("is_sweep", DataType::Boolean, false),
        Field::new("arrival_mono_ns", DataType::UInt64, false),
        Field::new("batch_id", DataType::UInt64, false),
    ]));
}
