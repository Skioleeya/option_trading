use crate::helpers::non_negative_volume_to_u64;
use crate::schema::ArrowMarketEvent;
use crate::threat::ThreatEngine;
use longport::quote::{PushDepth, PushQuote, SubFlags, Trade};
use num_traits::ToPrimitive;

pub fn l0_subscription_flags() -> SubFlags {
    SubFlags::QUOTE | SubFlags::DEPTH | SubFlags::TRADE
}

fn positive_or_none(value: f64) -> Option<f64> {
    if value > 0.0 { Some(value) } else { None }
}

pub fn quote_event(
    symbol: String,
    mono_ns: u64,
    seq_no: u64,
    detail: PushQuote,
) -> ArrowMarketEvent {
    ArrowMarketEvent {
        symbol,
        seq_no,
        event_type: 1,
        trade_type: None,
        trade_session: None,
        bid: None,
        ask: None,
        last_price: positive_or_none(detail.last_done.to_f64().unwrap_or_default()),
        volume: Some(non_negative_volume_to_u64(detail.volume)),
        bid_volume: None,
        ask_volume: None,
        current_volume: Some(non_negative_volume_to_u64(detail.current_volume)),
        turnover: Some(detail.turnover.to_f64().unwrap_or_default()),
        current_turnover: Some(detail.current_turnover.to_f64().unwrap_or_default()),
        impact_index: Some(0.0),
        is_sweep: false,
        arrival_mono_ns: mono_ns,
    }
}

pub fn trade_event(symbol: &str, mono_ns: u64, seq_no: u64, trade: Trade) -> ArrowMarketEvent {
    let trade_type = trade.trade_type.clone();
    let trade_session = format!("{:?}", trade.trade_session);
    ArrowMarketEvent {
        symbol: symbol.to_string(),
        seq_no,
        event_type: 3,
        trade_type: Some(trade_type.clone()),
        trade_session: Some(trade_session),
        bid: None,
        ask: None,
        last_price: positive_or_none(trade.price.to_f64().unwrap_or_default()),
        volume: Some(non_negative_volume_to_u64(trade.volume)),
        bid_volume: None,
        ask_volume: None,
        current_volume: None,
        turnover: None,
        current_turnover: None,
        impact_index: Some(0.0),
        is_sweep: trade_type.contains('F'),
        arrival_mono_ns: mono_ns,
    }
}

pub fn depth_event(
    symbol: &str,
    mono_ns: u64,
    seq_no: u64,
    detail: PushDepth,
    threat_engine: &mut ThreatEngine,
) -> ArrowMarketEvent {
    let bid = detail
        .bids
        .first()
        .and_then(|level| level.price)
        .and_then(|value| value.to_f64())
        .unwrap_or(0.0);
    let ask = detail
        .asks
        .first()
        .and_then(|level| level.price)
        .and_then(|value| value.to_f64())
        .unwrap_or(0.0);
    let bid_vol = detail
        .bids
        .first()
        .map(|level| non_negative_volume_to_u64(level.volume))
        .unwrap_or(0);
    let ask_vol = detail
        .asks
        .first()
        .map(|level| non_negative_volume_to_u64(level.volume))
        .unwrap_or(0);
    let impact_index = threat_engine.calculate_ofii(symbol, bid, bid_vol, ask, ask_vol);
    ArrowMarketEvent {
        symbol: symbol.to_string(),
        seq_no,
        event_type: 2,
        trade_type: None,
        trade_session: None,
        bid: positive_or_none(bid),
        ask: positive_or_none(ask),
        last_price: None,
        volume: None,
        bid_volume: Some(bid_vol),
        ask_volume: Some(ask_vol),
        current_volume: None,
        turnover: None,
        current_turnover: None,
        impact_index: Some(impact_index),
        is_sweep: false,
        arrival_mono_ns: mono_ns,
    }
}
