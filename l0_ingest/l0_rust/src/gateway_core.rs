use crate::gateway_event_map::{depth_event, l0_subscription_flags, quote_event, trade_event};
use crate::gateway_push_diag::{self, GatewayPushDiagnosticsHandle, RawSpyPushDiagnostics};
use crate::gateway_stress::run_stress_test;
use crate::helpers::now_unix_nanos;
use crate::ipc_writer::{ArrowBatchWriter, ArrowWriterConfig};
use crate::sdk_config::build_sdk_config;
use crate::schema::ArrowMarketEvent;
use crate::threat::ThreatEngine;
use longport::{
    quote::PushEventDetail,
    Config, QuoteContext,
};
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use std::sync::{Arc, Mutex};
use tokio::sync::{broadcast, mpsc};
use tokio::time::{self, Duration};
#[pyclass]
pub struct RustIngestGateway {
    pub config: Option<Arc<Config>>,
    pub runtime: tokio::runtime::Runtime,
    pub shutdown_tx: Option<broadcast::Sender<()>>,
    pub quote_ctx: Option<QuoteContext>,
    pub spy_push_diag: Arc<Mutex<RawSpyPushDiagnostics>>,
}
impl RustIngestGateway {
    fn configured_arc(&self) -> PyResult<Arc<Config>> {
        self.config
            .clone()
            .ok_or_else(|| PyRuntimeError::new_err("RustIngestGateway not configured"))
    }
    pub fn ensure_quote_ctx(&mut self) -> PyResult<()> {
        if self.quote_ctx.is_some() {
            return Ok(());
        }
        let config = self.configured_arc()?;
        let (ctx, _receiver) = self
            .runtime
            .block_on(QuoteContext::try_new(config))
            .map_err(|e| PyRuntimeError::new_err(format!("QuoteContext init failed: {e}")))?;
        self.quote_ctx = Some(ctx);
        Ok(())
    }
    pub fn clone_quote_ctx(&self) -> PyResult<QuoteContext> {
        self.quote_ctx
            .clone()
            .ok_or_else(|| PyRuntimeError::new_err("quote context unavailable"))
    }

    fn update_subscription(
        &mut self,
        symbols: Vec<String>,
        subscribe: bool,
    ) -> PyResult<()> {
        if symbols.is_empty() {
            return Ok(());
        }
        self.ensure_quote_ctx()?;
        let ctx = self.clone_quote_ctx()?;
        let flags = l0_subscription_flags();
        self.runtime
            .block_on(async move {
                if subscribe {
                    ctx.subscribe(symbols, flags, false).await
                } else {
                    ctx.unsubscribe(symbols, flags).await
                }
            })
            .map_err(|e| {
                let op = if subscribe { "subscribe" } else { "unsubscribe" };
                PyRuntimeError::new_err(format!("{op} failed: {e}"))
            })?;
        Ok(())
    }
}

#[pymethods]
impl RustIngestGateway {
    #[new]
    fn new() -> PyResult<Self> {
        let runtime = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .map_err(|e| PyRuntimeError::new_err(format!("Tokio runtime error: {e}")))?;
        Ok(Self {
            config: None,
            runtime,
            shutdown_tx: None,
            quote_ctx: None,
            spy_push_diag: gateway_push_diag::new_shared_diag(),
        })
    }
    #[pyo3(signature = (app_key, app_secret, access_token, http_url=None, quote_ws_url=None, trade_ws_url=None, language=None, enable_overnight=false))]
    fn configure(
        &mut self,
        app_key: String,
        app_secret: String,
        access_token: String,
        http_url: Option<String>,
        quote_ws_url: Option<String>,
        trade_ws_url: Option<String>,
        language: Option<String>,
        enable_overnight: bool,
    ) -> PyResult<()> {
        let config = Arc::new(build_sdk_config(
            app_key,
            app_secret,
            access_token,
            http_url,
            quote_ws_url,
            trade_ws_url,
            language,
            enable_overnight,
        )
        .map_err(|e| PyRuntimeError::new_err(format!("SDK config error: {e}")))?);
        self.config = Some(config);
        self.quote_ctx = None;
        Ok(())
    }
    #[pyo3(signature = (symbols, shm_path, cpu_id, batch_interval_ms, batch_max_rows, shm_capacity_bytes, signal_name))]
    fn start(
        &mut self,
        symbols: Vec<String>,
        shm_path: String,
        cpu_id: Option<usize>,
        batch_interval_ms: u64,
        batch_max_rows: usize,
        shm_capacity_bytes: usize,
        signal_name: String,
    ) -> PyResult<()> {
        if self.shutdown_tx.is_some() {
            self.stop()?;
        }
        let arrow_shm_path = format!("{shm_path}_arrow");
        let batch_writer = ArrowBatchWriter::create_or_open(
            &arrow_shm_path,
            ArrowWriterConfig::new(
                &arrow_shm_path,
                batch_interval_ms,
                batch_max_rows,
                shm_capacity_bytes,
                Some(signal_name),
            ),
        )
            .map_err(|err| PyRuntimeError::new_err(format!("arrow writer init failed: {err}")))?;
        let batch_interval_ms = batch_writer.batch_interval_ms();
        let config = self.configured_arc()?;
        let (ctx, mut receiver) = self
            .runtime
            .block_on(QuoteContext::try_new(config))
            .map_err(|e| PyRuntimeError::new_err(format!("QuoteContext init failed: {e}")))?;
        self.runtime
            .block_on(ctx.subscribe(symbols, l0_subscription_flags(), true))
            .map_err(|e| PyRuntimeError::new_err(format!("subscribe failed: {e}")))?;
        self.quote_ctx = Some(ctx.clone());
        gateway_push_diag::reset(&self.spy_push_diag);
        let spy_push_diag = Arc::clone(&self.spy_push_diag);
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
                                gateway_push_diag::record_quote(&spy_push_diag, &event.symbol);
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
                                gateway_push_diag::record_depth(&spy_push_diag, &event.symbol);
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
    #[pyo3(signature = (symbol, count, shm_path, batch_max_rows, signal_name, shm_capacity_bytes=0))]
    fn stress_test(
        &self,
        py: Python<'_>,
        symbol: String,
        count: u64,
        shm_path: String,
        batch_max_rows: usize,
        signal_name: String,
        shm_capacity_bytes: usize,
    ) -> PyResult<()> {
        py.allow_threads(move || {
            run_stress_test(
                symbol,
                count,
                shm_path,
                batch_max_rows,
                shm_capacity_bytes,
                signal_name,
            )
        })
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
    fn subscribe(&mut self, symbols: Vec<String>) -> PyResult<()> {
        self.update_subscription(symbols, true)
    }
    fn unsubscribe(&mut self, symbols: Vec<String>) -> PyResult<()> {
        self.update_subscription(symbols, false)
    }
    fn diagnostics(&self, py: Python<'_>) -> PyResult<PyObject> {
        gateway_push_diag::snapshot_to_pyobject(py, &self.spy_push_diag)
    }
    fn diagnostics_handle(&self) -> GatewayPushDiagnosticsHandle {
        GatewayPushDiagnosticsHandle::new(Arc::clone(&self.spy_push_diag))
    }
    fn stop(&mut self) -> PyResult<()> {
        if let Some(tx) = self.shutdown_tx.take() {
            let _ = tx.send(());
        }
        self.quote_ctx = None;
        Ok(())
    }
}
