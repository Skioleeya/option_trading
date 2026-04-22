use crate::helpers::now_unix_nanos;
use crate::ipc_writer::{ArrowBatchWriter, ArrowWriterConfig};
use crate::schema::ArrowMarketEvent;

pub fn run_stress_test(
    symbol: String,
    count: u64,
    shm_path: String,
    batch_max_rows: usize,
    shm_capacity_bytes: usize,
    signal_name: String,
) -> Result<(), String> {
    let config = ArrowWriterConfig::new(
        &shm_path,
        1,
        batch_max_rows,
        shm_capacity_bytes,
        Some(signal_name),
    );
    let mut batch_writer = ArrowBatchWriter::create_or_open(&shm_path, config)
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
            trade_type: Some("STRESS".to_string()),
            trade_session: Some("RTH".to_string()),
            bid: None,
            ask: None,
            last_price: Some(100.0 + (i as f64 * 0.01)),
            volume: Some(100),
            bid_volume: None,
            ask_volume: None,
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
