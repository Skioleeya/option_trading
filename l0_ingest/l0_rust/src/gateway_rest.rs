use crate::gateway_core::RustIngestGateway;
use crate::helpers::{
    decimal_to_f64, format_compact_date, option_direction_code, option_string, option_type_code, parse_calc_index,
    parse_iso_date,
};
use crate::rest_rows::{CalcIndexRow, OptionChainInfoRow, OptionExtendRow, OptionQuoteRow, QuoteRow};
use num_traits::ToPrimitive;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;

impl RustIngestGateway {
    pub(crate) fn rest_quote_impl(&mut self, symbols: Vec<String>) -> PyResult<String> {
        self.ensure_quote_ctx()?;
        let ctx = self.clone_quote_ctx()?;
        let rows = self
            .runtime
            .block_on(async move { ctx.quote(symbols).await })
            .map_err(|e| PyRuntimeError::new_err(format!("rest_quote failed: {e}")))?;
        let payload = rows
            .into_iter()
            .map(|q| QuoteRow {
                symbol: q.symbol,
                last_done: q.last_done.to_f64().unwrap_or_default(),
                volume: q.volume,
                turnover: q.turnover.to_f64().unwrap_or_default(),
                timestamp: q.timestamp.unix_timestamp(),
            })
            .collect::<Vec<_>>();
        serde_json::to_string(&payload).map_err(|e| PyRuntimeError::new_err(format!("json encode failed: {e}")))
    }

    pub(crate) fn rest_option_quote_impl(&mut self, symbols: Vec<String>) -> PyResult<String> {
        self.ensure_quote_ctx()?;
        let ctx = self.clone_quote_ctx()?;
        let rows = self
            .runtime
            .block_on(async move { ctx.option_quote(symbols).await })
            .map_err(|e| PyRuntimeError::new_err(format!("rest_option_quote failed: {e}")))?;
        let payload = rows
            .into_iter()
            .map(|q| OptionQuoteRow {
                symbol: q.symbol,
                last_done: decimal_to_f64(q.last_done),
                prev_close: decimal_to_f64(q.prev_close),
                open: decimal_to_f64(q.open),
                high: decimal_to_f64(q.high),
                low: decimal_to_f64(q.low),
                timestamp: q.timestamp.unix_timestamp(),
                volume: q.volume,
                turnover: decimal_to_f64(q.turnover),
                trade_status: q.trade_status as i32,
                option_extend: OptionExtendRow {
                    implied_volatility: q.implied_volatility.to_string(),
                    open_interest: q.open_interest,
                    expiry_date: format_compact_date(q.expiry_date),
                    strike_price: q.strike_price.to_string(),
                    contract_multiplier: q.contract_multiplier.to_string(),
                    contract_type: option_string(option_type_code(q.contract_type)),
                    contract_size: q.contract_size.to_string(),
                    direction: option_string(option_direction_code(q.direction)),
                    historical_volatility: q.historical_volatility.to_string(),
                    underlying_symbol: q.underlying_symbol.clone(),
                },
                open_interest: q.open_interest,
                implied_volatility: decimal_to_f64(q.implied_volatility),
                implied_volatility_raw: q.implied_volatility.to_string(),
                expiry_date: format_compact_date(q.expiry_date),
                expiry_date_raw: format_compact_date(q.expiry_date),
                strike_price: decimal_to_f64(q.strike_price),
                strike_price_raw: q.strike_price.to_string(),
                contract_multiplier: decimal_to_f64(q.contract_multiplier),
                contract_type: option_string(option_type_code(q.contract_type)),
                contract_size: decimal_to_f64(q.contract_size),
                direction: option_string(option_direction_code(q.direction)),
                historical_volatility: decimal_to_f64(q.historical_volatility),
                historical_volatility_raw: q.historical_volatility.to_string(),
                underlying_symbol: q.underlying_symbol,
            })
            .collect::<Vec<_>>();
        serde_json::to_string(&payload).map_err(|e| PyRuntimeError::new_err(format!("json encode failed: {e}")))
    }

    pub(crate) fn rest_option_chain_info_by_date_impl(
        &mut self,
        symbol: String,
        expiry_iso: String,
    ) -> PyResult<String> {
        self.ensure_quote_ctx()?;
        let ctx = self.clone_quote_ctx()?;
        let expiry_date = parse_iso_date(&expiry_iso)?;
        let rows = self
            .runtime
            .block_on(async move { ctx.option_chain_info_by_date(symbol, expiry_date).await })
            .map_err(|e| PyRuntimeError::new_err(format!("rest_option_chain_info_by_date failed: {e}")))?;
        let payload = rows
            .into_iter()
            .map(|v| OptionChainInfoRow {
                price: decimal_to_f64(v.price),
                price_raw: v.price.to_string(),
                strike_price: decimal_to_f64(v.price),
                call_symbol: v.call_symbol,
                put_symbol: v.put_symbol,
                standard: v.standard,
            })
            .collect::<Vec<_>>();
        serde_json::to_string(&payload).map_err(|e| PyRuntimeError::new_err(format!("json encode failed: {e}")))
    }

    pub(crate) fn rest_calc_indexes_impl(&mut self, symbols: Vec<String>, indexes: Vec<String>) -> PyResult<String> {
        self.ensure_quote_ctx()?;
        let ctx = self.clone_quote_ctx()?;
        let index_values = indexes
            .iter()
            .filter_map(|name| parse_calc_index(name))
            .collect::<Vec<_>>();
        if index_values.is_empty() {
            return Err(PyRuntimeError::new_err("rest_calc_indexes failed: no valid index names"));
        }
        let rows = self
            .runtime
            .block_on(async move { ctx.calc_indexes(symbols, index_values).await })
            .map_err(|e| PyRuntimeError::new_err(format!("rest_calc_indexes failed: {e}")))?;
        let payload = rows
            .into_iter()
            .map(|r| CalcIndexRow {
                symbol: r.symbol,
                last_done: r.last_done.and_then(|v| v.to_f64()),
                change_val: r.change_value.and_then(|v| v.to_f64()),
                change_rate: r.change_rate.and_then(|v| v.to_f64()),
                volume: r.volume,
                turnover: r.turnover.and_then(|v| v.to_f64()),
                expiry_date: r.expiry_date.map(format_compact_date),
                expiry_date_raw: r.expiry_date.map(format_compact_date),
                strike_price: r.strike_price.and_then(|v| v.to_f64()),
                strike_price_raw: r.strike_price.map(|v| v.to_string()),
                premium: r.premium.and_then(|v| v.to_f64()),
                open_interest: r.open_interest,
                implied_volatility: r.implied_volatility.and_then(|v| v.to_f64()),
                implied_volatility_raw: r.implied_volatility.map(|v| v.to_string()),
                delta: r.delta.and_then(|v| v.to_f64()),
                gamma: r.gamma.and_then(|v| v.to_f64()),
                theta: r.theta.and_then(|v| v.to_f64()),
                vega: r.vega.and_then(|v| v.to_f64()),
                rho: r.rho.and_then(|v| v.to_f64()),
            })
            .collect::<Vec<_>>();
        serde_json::to_string(&payload).map_err(|e| PyRuntimeError::new_err(format!("json encode failed: {e}")))
    }
}
