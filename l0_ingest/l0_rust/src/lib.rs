use crate::schema::InstitutionalMarketEvent;
use crate::threat::ThreatEngine;
use longport::{
    quote::{CalcIndex, PushEventDetail, SubFlags},
    Config, QuoteContext,
};
use num_traits::ToPrimitive;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use serde::Serialize;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use time::{format_description::parse as parse_time_format, Date};
use tokio::sync::broadcast;

pub mod ipc;
pub mod schema;
pub mod threat;

fn str_to_32(value: &str) -> [u8; 32] {
    let mut out = [0u8; 32];
    let bytes = value.as_bytes();
    let n = bytes.len().min(32);
    out[..n].copy_from_slice(&bytes[..n]);
    out
}

fn now_unix_nanos() -> u64 {
    match SystemTime::now().duration_since(UNIX_EPOCH) {
        Ok(duration) => duration.as_nanos() as u64,
        Err(_) => 0,
    }
}

fn parse_calc_index(name: &str) -> Option<CalcIndex> {
    match name.trim() {
        "LastDone" => Some(CalcIndex::LastDone),
        "ChangeValue" => Some(CalcIndex::ChangeValue),
        "ChangeRate" => Some(CalcIndex::ChangeRate),
        "Volume" => Some(CalcIndex::Volume),
        "Turnover" => Some(CalcIndex::Turnover),
        "YtdChangeRate" => Some(CalcIndex::YtdChangeRate),
        "TurnoverRate" => Some(CalcIndex::TurnoverRate),
        "TotalMarketValue" => Some(CalcIndex::TotalMarketValue),
        "CapitalFlow" => Some(CalcIndex::CapitalFlow),
        "Amplitude" => Some(CalcIndex::Amplitude),
        "VolumeRatio" => Some(CalcIndex::VolumeRatio),
        "PeTtmRatio" => Some(CalcIndex::PeTtmRatio),
        "PbRatio" => Some(CalcIndex::PbRatio),
        "DividendRatioTtm" => Some(CalcIndex::DividendRatioTtm),
        "FiveDayChangeRate" => Some(CalcIndex::FiveDayChangeRate),
        "TenDayChangeRate" => Some(CalcIndex::TenDayChangeRate),
        "HalfYearChangeRate" => Some(CalcIndex::HalfYearChangeRate),
        "FiveMinutesChangeRate" => Some(CalcIndex::FiveMinutesChangeRate),
        "ExpiryDate" => Some(CalcIndex::ExpiryDate),
        "StrikePrice" => Some(CalcIndex::StrikePrice),
        "UpperStrikePrice" => Some(CalcIndex::UpperStrikePrice),
        "LowerStrikePrice" => Some(CalcIndex::LowerStrikePrice),
        "OutstandingQty" => Some(CalcIndex::OutstandingQty),
        "OutstandingRatio" => Some(CalcIndex::OutstandingRatio),
        "Premium" => Some(CalcIndex::Premium),
        "ItmOtm" => Some(CalcIndex::ItmOtm),
        "ImpliedVolatility" => Some(CalcIndex::ImpliedVolatility),
        "WarrantDelta" => Some(CalcIndex::WarrantDelta),
        "CallPrice" => Some(CalcIndex::CallPrice),
        "ToCallPrice" => Some(CalcIndex::ToCallPrice),
        "EffectiveLeverage" => Some(CalcIndex::EffectiveLeverage),
        "LeverageRatio" => Some(CalcIndex::LeverageRatio),
        "ConversionRatio" => Some(CalcIndex::ConversionRatio),
        "BalancePoint" => Some(CalcIndex::BalancePoint),
        "OpenInterest" => Some(CalcIndex::OpenInterest),
        "Delta" => Some(CalcIndex::Delta),
        "Gamma" => Some(CalcIndex::Gamma),
        "Theta" => Some(CalcIndex::Theta),
        "Vega" => Some(CalcIndex::Vega),
        "Rho" => Some(CalcIndex::Rho),
        _ => None,
    }
}

fn parse_iso_date(value: &str) -> PyResult<Date> {
    let format =
        parse_time_format("[year]-[month]-[day]").map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    Date::parse(value, &format).map_err(|e| PyRuntimeError::new_err(format!("invalid date '{value}': {e}")))
}

#[derive(Serialize)]
struct QuoteRow {
    symbol: String,
    last_done: f64,
    volume: i64,
    turnover: f64,
    timestamp: i64,
}

#[derive(Serialize)]
struct OptionQuoteRow {
    symbol: String,
    last_done: f64,
    volume: i64,
    open_interest: i64,
    implied_volatility: f64,
}

#[derive(Serialize)]
struct OptionChainInfoRow {
    price: f64,
    call_symbol: String,
    put_symbol: String,
}

#[derive(Serialize)]
struct CalcIndexRow {
    symbol: String,
    volume: Option<i64>,
    open_interest: Option<i64>,
    implied_volatility: Option<f64>,
    delta: Option<f64>,
    gamma: Option<f64>,
    theta: Option<f64>,
    vega: Option<f64>,
    rho: Option<f64>,
}

#[pyclass]
pub struct RustIngestGateway {
    config: Arc<Config>,
    runtime: tokio::runtime::Runtime,
    shutdown_tx: Option<broadcast::Sender<()>>,
    quote_ctx: Option<QuoteContext>,
}

impl RustIngestGateway {
    fn ensure_quote_ctx(&mut self) -> PyResult<()> {
        if self.quote_ctx.is_some() {
            return Ok(());
        }
        let (ctx, _receiver) = self
            .runtime
            .block_on(QuoteContext::try_new(self.config.clone()))
            .map_err(|e| PyRuntimeError::new_err(format!("QuoteContext init failed: {e}")))?;
        self.quote_ctx = Some(ctx);
        Ok(())
    }

    fn clone_quote_ctx(&self) -> PyResult<QuoteContext> {
        self.quote_ctx
            .clone()
            .ok_or_else(|| PyRuntimeError::new_err("quote context unavailable"))
    }
}

#[pymethods]
impl RustIngestGateway {
    #[new]
    fn new() -> PyResult<Self> {
        let config = Arc::new(
            Config::from_env().map_err(|e| PyRuntimeError::new_err(format!("SDK config error: {e}")))?,
        );
        let runtime = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .map_err(|e| PyRuntimeError::new_err(format!("Tokio runtime error: {e}")))?;

        Ok(Self {
            config,
            runtime,
            shutdown_tx: None,
            quote_ctx: None,
        })
    }

    fn start(&mut self, symbols: Vec<String>, shm_path: String, cpu_id: Option<usize>) -> PyResult<()> {
        if self.shutdown_tx.is_some() {
            self.stop()?;
        }

        let shm = match crate::ipc::IpcProducer::new(&shm_path).create() {
            Ok(shm) => shm,
            Err(shared_memory::ShmemError::MappingIdExists) => {
                println!("[RustGateway] SHM {} already exists, joining...", shm_path);
                crate::ipc::IpcProducer::new(&shm_path)
                    .open()
                    .map_err(|e| PyRuntimeError::new_err(format!("failed to open SHM: {e:?}")))?
            }
            Err(e) => {
                return Err(PyRuntimeError::new_err(format!("failed to create SHM: {e:?}")));
            }
        };
        let producer = crate::ipc::IpcProducer::from_shmem(shm);

        let (ctx, mut receiver) = self
            .runtime
            .block_on(QuoteContext::try_new(self.config.clone()))
            .map_err(|e| PyRuntimeError::new_err(format!("QuoteContext init failed: {e}")))?;
        self.runtime
            .block_on(ctx.subscribe(symbols, SubFlags::all(), true))
            .map_err(|e| PyRuntimeError::new_err(format!("subscribe failed: {e}")))?;
        self.quote_ctx = Some(ctx.clone());

        let (tx, mut rx) = broadcast::channel(1);
        self.shutdown_tx = Some(tx);

        self.runtime.spawn(async move {
            if let Some(id) = cpu_id {
                if let Err(err) = affinity::set_thread_affinity(&[id]) {
                    println!("[RustGateway] Affinity set failed for core {}: {:?}", id, err);
                } else {
                    println!("[RustGateway] Thread pinned to core {}", id);
                }
            }

            let mut threat_engine = ThreatEngine::new();
            loop {
                tokio::select! {
                    _ = rx.recv() => {
                        println!("[RustGateway] Shutdown signal received.");
                        break;
                    }
                    Some(event) = receiver.recv() => {
                        let mono_ns = now_unix_nanos();
                        let symbol = event.symbol.clone();
                        match event.detail {
                            PushEventDetail::Quote(q) => {
                                let ev = InstitutionalMarketEvent {
                                    symbol: str_to_32(&symbol),
                                    seq_no: 0,
                                    event_type: 1,
                                    bid: 0.0,
                                    ask: 0.0,
                                    last_price: q.last_done.to_f64().unwrap_or_default(),
                                    spot: 0.0,
                                    volume: q.volume as u64,
                                    open_interest: 0,
                                    implied_volatility: 0.0,
                                    impact_index: 0.0,
                                    is_sweep: false,
                                    ttm_seconds: 0.0,
                                    arrival_mono_ns: mono_ns,
                                    sequence_id: 0,
                                };
                                let _ = producer.push(&ev);
                            }
                            PushEventDetail::Trade(t) => {
                                for trade in t.trades {
                                    let ev = InstitutionalMarketEvent {
                                        symbol: str_to_32(&symbol),
                                        seq_no: 0,
                                        event_type: 3,
                                        bid: 0.0,
                                        ask: 0.0,
                                        last_price: trade.price.to_f64().unwrap_or_default(),
                                        spot: 0.0,
                                        volume: trade.volume as u64,
                                        open_interest: 0,
                                        implied_volatility: 0.0,
                                        impact_index: 0.0,
                                        is_sweep: trade.trade_type.contains('F'),
                                        ttm_seconds: 0.0,
                                        arrival_mono_ns: mono_ns,
                                        sequence_id: 0,
                                    };
                                    let _ = producer.push(&ev);
                                }
                            }
                            PushEventDetail::Depth(d) => {
                                let bid = d
                                    .bids
                                    .first()
                                    .and_then(|b| b.price)
                                    .and_then(|p| p.to_f64())
                                    .unwrap_or(0.0);
                                let ask = d
                                    .asks
                                    .first()
                                    .and_then(|a| a.price)
                                    .and_then(|p| p.to_f64())
                                    .unwrap_or(0.0);
                                let bid_vol = d.bids.first().map(|b| b.volume as u64).unwrap_or(0);
                                let ask_vol = d.asks.first().map(|a| a.volume as u64).unwrap_or(0);
                                let impact = threat_engine.calculate_ofii(&symbol, bid, bid_vol, ask, ask_vol);
                                let ev = InstitutionalMarketEvent {
                                    symbol: str_to_32(&symbol),
                                    seq_no: 0,
                                    event_type: 2,
                                    bid,
                                    ask,
                                    last_price: 0.0,
                                    spot: 0.0,
                                    volume: 0,
                                    open_interest: 0,
                                    implied_volatility: 0.0,
                                    impact_index: impact,
                                    is_sweep: false,
                                    ttm_seconds: 0.0,
                                    arrival_mono_ns: mono_ns,
                                    sequence_id: 0,
                                };
                                let _ = producer.push(&ev);
                            }
                            _ => {}
                        }
                    }
                }
            }
        });

        Ok(())
    }

    fn rest_quote(&mut self, symbols: Vec<String>) -> PyResult<String> {
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

    fn rest_option_quote(&mut self, symbols: Vec<String>) -> PyResult<String> {
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
                last_done: q.last_done.to_f64().unwrap_or_default(),
                volume: q.volume,
                open_interest: q.open_interest,
                implied_volatility: q.implied_volatility.to_f64().unwrap_or_default(),
            })
            .collect::<Vec<_>>();
        serde_json::to_string(&payload).map_err(|e| PyRuntimeError::new_err(format!("json encode failed: {e}")))
    }

    fn rest_option_chain_info_by_date(&mut self, symbol: String, expiry_iso: String) -> PyResult<String> {
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
                price: v.price.to_f64().unwrap_or_default(),
                call_symbol: v.call_symbol,
                put_symbol: v.put_symbol,
            })
            .collect::<Vec<_>>();
        serde_json::to_string(&payload).map_err(|e| PyRuntimeError::new_err(format!("json encode failed: {e}")))
    }

    fn rest_calc_indexes(&mut self, symbols: Vec<String>, indexes: Vec<String>) -> PyResult<String> {
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
                volume: r.volume,
                open_interest: r.open_interest,
                implied_volatility: r.implied_volatility.and_then(|v| v.to_f64()),
                delta: r.delta.and_then(|v| v.to_f64()),
                gamma: r.gamma.and_then(|v| v.to_f64()),
                theta: r.theta.and_then(|v| v.to_f64()),
                vega: r.vega.and_then(|v| v.to_f64()),
                rho: r.rho.and_then(|v| v.to_f64()),
            })
            .collect::<Vec<_>>();
        serde_json::to_string(&payload).map_err(|e| PyRuntimeError::new_err(format!("json encode failed: {e}")))
    }

    fn stress_test(&self, symbol: String, count: u64, shm_path: String) -> PyResult<()> {
        let shm = crate::ipc::IpcProducer::new(&shm_path)
            .open()
            .map_err(|e| PyRuntimeError::new_err(format!("stress test open SHM failed: {e:?}")))?;
        let producer = crate::ipc::IpcProducer::from_shmem(shm);
        let ev_symbol = str_to_32(&symbol);

        println!(
            "[RustGateway] Starting stress test: sending {} events for {}",
            count, symbol
        );
        let start = std::time::Instant::now();

        for i in 0..count {
            let ev = InstitutionalMarketEvent {
                symbol: ev_symbol,
                seq_no: i,
                event_type: 3,
                bid: 0.0,
                ask: 0.0,
                last_price: 100.0 + (i as f64 * 0.01),
                spot: 0.0,
                volume: 100,
                open_interest: 0,
                implied_volatility: 0.0,
                impact_index: 0.0,
                is_sweep: false,
                ttm_seconds: 0.0,
                arrival_mono_ns: now_unix_nanos(),
                sequence_id: i as i64,
            };
            while !producer.push(&ev) {
                std::hint::spin_loop();
            }
        }

        let duration = start.elapsed();
        println!(
            "[RustGateway] Stress test complete. Time: {:?}, Rate: {:.2} events/sec",
            duration,
            count as f64 / duration.as_secs_f64()
        );
        Ok(())
    }

    fn stop(&mut self) -> PyResult<()> {
        if let Some(tx) = self.shutdown_tx.take() {
            let _ = tx.send(());
        }
        self.quote_ctx = None;
        Ok(())
    }
}

#[pymodule]
fn l0_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustIngestGateway>()?;
    Ok(())
}
