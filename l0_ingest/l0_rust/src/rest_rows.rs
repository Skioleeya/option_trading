use serde::Serialize;

#[derive(Serialize)]
pub struct QuoteRow {
    pub symbol: String,
    pub last_done: f64,
    pub volume: i64,
    pub turnover: f64,
    pub timestamp: i64,
}

#[derive(Serialize)]
pub struct OptionExtendRow {
    pub implied_volatility: String,
    pub open_interest: i64,
    pub expiry_date: String,
    pub strike_price: String,
    pub contract_multiplier: String,
    pub contract_type: Option<String>,
    pub contract_size: String,
    pub direction: Option<String>,
    pub historical_volatility: String,
    pub underlying_symbol: String,
}

#[derive(Serialize)]
pub struct OptionQuoteRow {
    pub symbol: String,
    pub last_done: f64,
    pub prev_close: f64,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub timestamp: i64,
    pub volume: i64,
    pub turnover: f64,
    pub trade_status: i32,
    pub option_extend: OptionExtendRow,
    pub open_interest: i64,
    pub implied_volatility: f64,
    pub implied_volatility_raw: String,
    pub expiry_date: String,
    pub expiry_date_raw: String,
    pub strike_price: f64,
    pub strike_price_raw: String,
    pub contract_multiplier: f64,
    pub contract_type: Option<String>,
    pub contract_size: f64,
    pub direction: Option<String>,
    pub historical_volatility: f64,
    pub historical_volatility_raw: String,
    pub underlying_symbol: String,
}

#[derive(Serialize)]
pub struct OptionChainInfoRow {
    pub price: f64,
    pub price_raw: String,
    pub strike_price: f64,
    pub call_symbol: String,
    pub put_symbol: String,
    pub standard: bool,
}

#[derive(Serialize)]
pub struct CalcIndexRow {
    pub symbol: String,
    pub last_done: Option<f64>,
    pub change_val: Option<f64>,
    pub change_rate: Option<f64>,
    pub volume: Option<i64>,
    pub turnover: Option<f64>,
    pub expiry_date: Option<String>,
    pub expiry_date_raw: Option<String>,
    pub strike_price: Option<f64>,
    pub strike_price_raw: Option<String>,
    pub premium: Option<f64>,
    pub open_interest: Option<i64>,
    pub implied_volatility: Option<f64>,
    pub implied_volatility_raw: Option<String>,
    pub delta: Option<f64>,
    pub gamma: Option<f64>,
    pub theta: Option<f64>,
    pub vega: Option<f64>,
    pub rho: Option<f64>,
}
