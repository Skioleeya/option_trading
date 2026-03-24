use crate::helpers::{non_negative_volume_to_u64, now_unix_nanos, str_to_32};
use crate::schema::InstitutionalMarketEvent;
use crate::threat::ThreatEngine;
use longport::{
    quote::{PushEventDetail, SubFlags},
    Config, QuoteContext,
};
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use std::sync::Arc;
use tokio::sync::broadcast;

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
            Err(e) => return Err(PyRuntimeError::new_err(format!("failed to create SHM: {e:?}"))),
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
                                let current_volume = non_negative_volume_to_u64(q.current_volume);
                                let reported_volume = non_negative_volume_to_u64(q.volume);
                                let ev = InstitutionalMarketEvent {
                                    symbol: str_to_32(&symbol),
                                    seq_no: 0,
                                    event_type: 1,
                                    bid: 0.0,
                                    ask: 0.0,
                                    last_price: q.last_done.to_f64().unwrap_or_default(),
                                    spot: 0.0,
                                    volume: reported_volume,
                                    open_interest: 0,
                                    implied_volatility: 0.0,
                                    impact_index: 0.0,
                                    is_sweep: false,
                                    ttm_seconds: 0.0,
                                    arrival_mono_ns: mono_ns,
                                    sequence_id: 0,
                                    current_volume,
                                    turnover: q.turnover.to_f64().unwrap_or_default(),
                                    current_turnover: q.current_turnover.to_f64().unwrap_or_default(),
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
                                        volume: non_negative_volume_to_u64(trade.volume),
                                        open_interest: 0,
                                        implied_volatility: 0.0,
                                        impact_index: 0.0,
                                        is_sweep: trade.trade_type.contains('F'),
                                        ttm_seconds: 0.0,
                                        arrival_mono_ns: mono_ns,
                                        sequence_id: 0,
                                        current_volume: 0,
                                        turnover: 0.0,
                                        current_turnover: 0.0,
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
                                let bid_vol = d
                                    .bids
                                    .first()
                                    .map(|b| non_negative_volume_to_u64(b.volume))
                                    .unwrap_or(0);
                                let ask_vol = d
                                    .asks
                                    .first()
                                    .map(|a| non_negative_volume_to_u64(a.volume))
                                    .unwrap_or(0);
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
                                    current_volume: 0,
                                    turnover: 0.0,
                                    current_turnover: 0.0,
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
                current_volume: 0,
                turnover: 0.0,
                current_turnover: 0.0,
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
