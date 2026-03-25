use crate::helpers::{non_negative_volume_to_u64, now_unix_nanos};
use crate::ipc_writer::ArrowBatchWriter;
use crate::schema::ArrowMarketEvent;
use crate::threat::ThreatEngine;
use longport::{
    quote::{PushEventDetail, SubFlags},
    Config, QuoteContext,
};
use num_traits::ToPrimitive;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use std::sync::Arc;
use tokio::sync::{broadcast, mpsc};
use tokio::time::{self, Duration};

#[pyclass]
pub struct RustIngestGateway {
    pub config: Arc<Config>,
    pub runtime: tokio::runtime::Runtime,
    pub shutdown_tx: Option<broadcast::Sender<()>>,
    pub quote_ctx: Option<QuoteContext>,
}

impl RustIngestGateway {
    pub fn ensure_quote_ctx(&mut self) -> PyResult<()> {
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

    pub fn clone_quote_ctx(&self) -> PyResult<QuoteContext> {
        self.quote_ctx
            .clone()
            .ok_or_else(|| PyRuntimeError::new_err("quote context unavailable"))
    }
}

fn l0_subscription_flags() -> SubFlags {
    SubFlags::QUOTE | SubFlags::DEPTH | SubFlags::TRADE
}

fn positive_or_none(value: f64) -> Option<f64> {
    if value > 0.0 {
        Some(value)
    } else {
        None
    }
}

fn quote_event(symbol: String, mono_ns: u64, seq_no: u64, detail: longport::quote::PushQuote) -> ArrowMarketEvent {
    ArrowMarketEvent {
        symbol,
        seq_no,
        event_type: 1,
        bid: None,
        ask: None,
        last_price: positive_or_none(detail.last_done.to_f64().unwrap_or_default()),
        volume: Some(non_negative_volume_to_u64(detail.volume)),
        current_volume: Some(non_negative_volume_to_u64(detail.current_volume)),
        turnover: Some(detail.turnover.to_f64().unwrap_or_default()),
        current_turnover: Some(detail.current_turnover.to_f64().unwrap_or_default()),
        impact_index: Some(0.0),
        is_sweep: false,
        arrival_mono_ns: mono_ns,
    }
}

fn trade_event(
    symbol: &str,
    mono_ns: u64,
    seq_no: u64,
    trade: longport::quote::Trade,
) -> ArrowMarketEvent {
    ArrowMarketEvent {
        symbol: symbol.to_string(),
        seq_no,
        event_type: 3,
        bid: None,
        ask: None,
        last_price: positive_or_none(trade.price.to_f64().unwrap_or_default()),
        volume: Some(non_negative_volume_to_u64(trade.volume)),
        current_volume: None,
        turnover: None,
        current_turnover: None,
        impact_index: Some(0.0),
        is_sweep: trade.trade_type.contains('F'),
        arrival_mono_ns: mono_ns,
    }
}

fn depth_event(
    symbol: &str,
    mono_ns: u64,
    seq_no: u64,
    detail: longport::quote::PushDepth,
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
        bid: positive_or_none(bid),
        ask: positive_or_none(ask),
        last_price: None,
        volume: None,
        current_volume: None,
        turnover: None,
        current_turnover: None,
        impact_index: Some(impact_index),
        is_sweep: false,
        arrival_mono_ns: mono_ns,
    }
}

fn run_stress_test(symbol: String, count: u64, shm_path: String) -> Result<(), String> {
    let mut batch_writer = ArrowBatchWriter::create_or_open(&shm_path)
        .map_err(|err| format!("stress test writer init failed: {err}"))?;

    println!(
        "[RustGateway] Starting Arrow IPC stress test: sending {} events for {}",
        count, symbol
    );
    let start = std::time::Instant::now();

    for i in 0..count {
        let event = ArrowMarketEvent {
            symbol: symbol.clone(),
            seq_no: i,
            event_type: 3,
            bid: None,
            ask: None,
            last_price: Some(100.0 + (i as f64 * 0.01)),
            volume: Some(100),
            current_volume: Some(1),
            turnover: Some(0.0),
            current_turnover: Some(0.0),
            impact_index: Some(0.0),
            is_sweep: false,
            arrival_mono_ns: now_unix_nanos(),
        };
        batch_writer
            .push_event(event)
            .map_err(|err| format!("stress test push failed: {err}"))?;
    }
    batch_writer
        .flush()
        .map_err(|err| format!("stress test flush failed: {err}"))?;

    let duration = start.elapsed();
    println!(
        "[RustGateway] Stress test complete. Time: {:?}, Rate: {:.2} events/sec",
        duration,
        count as f64 / duration.as_secs_f64()
    );
    Ok(())
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

    #[pyo3(signature = (symbols, shm_path, cpu_id=None))]
    fn start(&mut self, symbols: Vec<String>, shm_path: String, cpu_id: Option<usize>) -> PyResult<()> {
        if self.shutdown_tx.is_some() {
            self.stop()?;
        }

        let arrow_shm_path = format!("{shm_path}_arrow");
        let batch_writer = ArrowBatchWriter::create_or_open(&arrow_shm_path)
            .map_err(|err| PyRuntimeError::new_err(format!("arrow writer init failed: {err}")))?;
        let batch_interval_ms = batch_writer.batch_interval_ms();

        let (ctx, mut receiver) = self
            .runtime
            .block_on(QuoteContext::try_new(self.config.clone()))
            .map_err(|e| PyRuntimeError::new_err(format!("QuoteContext init failed: {e}")))?;
        self.runtime
            .block_on(ctx.subscribe(symbols, l0_subscription_flags(), true))
            .map_err(|e| PyRuntimeError::new_err(format!("subscribe failed: {e}")))?;
        self.quote_ctx = Some(ctx.clone());

        let (event_tx, event_rx) = mpsc::unbounded_channel::<ArrowMarketEvent>();
        let (tx, _) = broadcast::channel(1);
        self.shutdown_tx = Some(tx);
        let mut ingest_shutdown = self
            .shutdown_tx
            .as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("shutdown channel missing"))?
            .subscribe();
        let mut flush_shutdown = self
            .shutdown_tx
            .as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("shutdown channel missing"))?
            .subscribe();

        self.runtime.spawn(async move {
            let mut threat_engine = ThreatEngine::new();
            let mut seq_no: u64 = 0;
            loop {
                tokio::select! {
                    _ = ingest_shutdown.recv() => {
                        println!("[RustGateway] Ingest shutdown signal received.");
                        break;
                    }
                    Some(event) = receiver.recv() => {
                        let mono_ns = now_unix_nanos();
                        let mapped = match event.detail {
                            PushEventDetail::Quote(quote) => {
                                Some(quote_event(event.symbol, mono_ns, seq_no, quote))
                            }
                            PushEventDetail::Trade(trades) => {
                                for trade in trades.trades {
                                    let row = trade_event(&event.symbol, mono_ns, seq_no, trade);
                                    let _ = event_tx.send(row);
                                    seq_no = seq_no.saturating_add(1);
                                }
                                None
                            }
                            PushEventDetail::Depth(depth) => {
                                Some(depth_event(&event.symbol, mono_ns, seq_no, depth, &mut threat_engine))
                            }
                            _ => None,
                        };
                        if let Some(row) = mapped {
                            let _ = event_tx.send(row);
                            seq_no = seq_no.saturating_add(1);
                        }
                    }
                }
            }
        });

        self.runtime.spawn(async move {
            if let Some(id) = cpu_id {
                if let Err(err) = affinity::set_thread_affinity(&[id]) {
                    println!("[RustGateway] Affinity set failed for core {}: {:?}", id, err);
                } else {
                    println!("[RustGateway] Thread pinned to core {}", id);
                }
            }

            let mut batch_writer = batch_writer;
            let mut flush_timer = time::interval(Duration::from_millis(batch_interval_ms));
            let mut event_rx = event_rx;
            loop {
                tokio::select! {
                    _ = flush_shutdown.recv() => {
                        let _ = batch_writer.flush();
                        println!("[RustGateway] Flush shutdown signal received.");
                        break;
                    }
                    _ = flush_timer.tick() => {
                        let _ = batch_writer.flush();
                    }
                    maybe_event = event_rx.recv() => {
                        match maybe_event {
                            Some(event) => {
                                if let Err(err) = batch_writer.push_event(event) {
                                    println!("[RustGateway] Arrow batch write failed: {}", err);
                                }
                            }
                            None => {
                                let _ = batch_writer.flush();
                                break;
                            }
                        }
                    }
                }
            }
        });

        Ok(())
    }

    fn stress_test(&self, py: Python<'_>, symbol: String, count: u64, shm_path: String) -> PyResult<()> {
        py.allow_threads(move || run_stress_test(symbol, count, shm_path))
            .map_err(PyRuntimeError::new_err)
    }

    fn rest_quote(&mut self, symbols: Vec<String>) -> PyResult<String> {
        self.rest_quote_impl(symbols)
    }

    fn rest_option_quote(&mut self, symbols: Vec<String>) -> PyResult<String> {
        self.rest_option_quote_impl(symbols)
    }

    fn rest_option_chain_info_by_date(&mut self, symbol: String, expiry_iso: String) -> PyResult<String> {
        self.rest_option_chain_info_by_date_impl(symbol, expiry_iso)
    }

    fn rest_calc_indexes(&mut self, symbols: Vec<String>, indexes: Vec<String>) -> PyResult<String> {
        self.rest_calc_indexes_impl(symbols, indexes)
    }

    fn stop(&mut self) -> PyResult<()> {
        if let Some(tx) = self.shutdown_tx.take() {
            let _ = tx.send(());
        }
        self.quote_ctx = None;
        Ok(())
    }
}
