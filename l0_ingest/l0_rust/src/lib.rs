use pyo3::prelude::*;
use std::sync::Arc;
use tokio::sync::broadcast;
use longport::{Config, QuoteContext, quote::SubFlags, quote::PushEvent, quote::PushEventDetail};
use num_traits::ToPrimitive;
use crate::schema::InstitutionalMarketEvent;
use crate::threat::ThreatEngine;

pub mod schema;
pub mod ipc;
pub mod threat;

fn str_to_32(s: &str) -> [u8; 32] {
    let mut bytes = [0u8; 32];
    let s_bytes = s.as_bytes();
    let len = std::cmp::min(s_bytes.len(), 32);
    bytes[..len].copy_from_slice(&s_bytes[..len]);
    bytes
}

#[pyclass]
pub struct RustIngestGateway {
    config: Arc<Config>,
    runtime: tokio::runtime::Runtime,
    shutdown_tx: Option<broadcast::Sender<()>>,
}

#[pymethods]
impl RustIngestGateway {
    #[new]
    fn new() -> PyResult<Self> {
        let config = Arc::new(Config::from_env().map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("SDK Config Error: {}", e)))?);
        let runtime = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Tokio Error: {}", e)))?;
        
        Ok(RustIngestGateway { 
            config, 
            runtime,
            shutdown_tx: None,
        })
    }

    fn start(&mut self, symbols: Vec<String>, shm_path: String, cpu_id: Option<usize>) -> PyResult<()> {
        let config = self.config.clone();
        let (tx, mut rx) = broadcast::channel(1);
        self.shutdown_tx = Some(tx);
        
        self.runtime.spawn(async move {
            if let Some(id) = cpu_id {
                affinity::set_thread_affinity(&[id]).unwrap();
                println!("[RustGateway] Thread pinned to core {}", id);
            }
            let shm = match crate::ipc::IpcProducer::new(&shm_path).create() {
                Ok(s) => s,
                Err(shared_memory::ShmemError::MappingIdExists) => {
                    println!("[RustGateway] SHM {} already exists, joining...", shm_path);
                    crate::ipc::IpcProducer::new(&shm_path).open().unwrap()
                }
                Err(e) => panic!("Failed to create SHM: {:?}", e),
            };
            let producer = crate::ipc::IpcProducer::from_shmem(shm);
            
            let (ctx, mut receiver) = QuoteContext::try_new(config).await.unwrap();
            ctx.subscribe(symbols, SubFlags::all(), true).await.unwrap();
            
            let mut threat_engine = ThreatEngine::new();
            
            loop {
                tokio::select! {
                    _ = rx.recv() => {
                        println!("[RustGateway] Shutdown signal received.");
                        break;
                    }
                    Some(event) = receiver.recv() => {
                        let mono_ns = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos() as u64;
                        let symbol = event.symbol.clone();
                        
                        match event.detail {
                            PushEventDetail::Quote(q) => {
                                let ev = InstitutionalMarketEvent {
                                    symbol: str_to_32(&symbol),
                                    seq_no: 0,
                                    event_type: 1,
                                    bid: 0.0, // Level 1 info might be in Depth
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
                                producer.push(&ev);
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
                                    producer.push(&ev);
                                }
                            }
                            PushEventDetail::Depth(d) => {
                                let bid = d.bids.first().and_then(|b| b.price).and_then(|p| p.to_f64()).unwrap_or(0.0);
                                let ask = d.asks.first().and_then(|a| a.price).and_then(|p| p.to_f64()).unwrap_or(0.0);
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
                                producer.push(&ev);
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
        let shm = crate::ipc::IpcProducer::new(&shm_path).open().unwrap();
        let producer = crate::ipc::IpcProducer::from_shmem(shm);
        let ev_symbol = str_to_32(&symbol);
        
        println!("[RustGateway] Starting stress test: sending {} events for {}", count, symbol);
        let start = std::time::Instant::now();
        
        for i in 0..count {
            let ev = InstitutionalMarketEvent {
                symbol: ev_symbol,
                seq_no: i,
                event_type: 3, // Trade
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
                arrival_mono_ns: std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos() as u64,
                sequence_id: i as i64,
            };
            while !producer.push(&ev) {
                std::hint::spin_loop();
            }
        }
        
        let duration = start.elapsed();
        println!("[RustGateway] Stress test complete. Time: {:?}, Rate: {:.2} events/sec", 
                 duration, count as f64 / duration.as_secs_f64());
        Ok(())
    }

    fn stop(&mut self) -> PyResult<()> {
        if let Some(tx) = self.shutdown_tx.take() {
            let _ = tx.send(());
        }
        Ok(())
    }
}

#[pymodule]
fn l0_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustIngestGateway>()?;
    Ok(())
}
