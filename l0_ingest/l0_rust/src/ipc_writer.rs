use crate::arrow_ipc::{ArrowIpcSegment, DEFAULT_ARROW_IPC_BYTES};
use crate::schema::{ArrowMarketEvent, ARROW_IPC_SCHEMA};
use crate::transport_contract::{
    resolve_arrow_signal_name, DEFAULT_L0_IPC_SHM_BYTES,
};
use crate::windows_signal::WindowsSignal;
use arrow::array::{ArrayRef, BooleanArray, Float64Array, StringArray, UInt64Array, UInt8Array};
use arrow::ipc::writer::StreamWriter;
use arrow::record_batch::RecordBatch;
use std::io::Cursor;
use std::sync::Arc;

#[derive(Debug, Clone)]
pub struct ArrowWriterConfig {
    pub batch_interval_ms: u64,
    pub batch_max_rows: usize,
    pub shm_capacity_bytes: usize,
    pub signal_name: String,
}

impl ArrowWriterConfig {
    pub fn new(
        shm_name: &str,
        batch_interval_ms: u64,
        batch_max_rows: usize,
        shm_capacity_bytes: usize,
        signal_name: Option<String>,
    ) -> Self {
        Self {
            batch_interval_ms: batch_interval_ms.max(1),
            batch_max_rows: batch_max_rows.max(1),
            shm_capacity_bytes: normalize_shm_capacity_bytes(shm_capacity_bytes),
            signal_name: resolve_arrow_signal_name(shm_name, signal_name.as_deref()),
        }
    }
}

pub struct ArrowBatchWriter {
    config: ArrowWriterConfig,
    segment: ArrowIpcSegment,
    signal: WindowsSignal,
    rows: Vec<ArrowMarketEvent>,
    next_batch_id: u64,
}

impl ArrowBatchWriter {
    pub fn create_or_open(shm_name: &str, config: ArrowWriterConfig) -> Result<Self, String> {
        let segment = ArrowIpcSegment::create_or_open(shm_name, config.shm_capacity_bytes)
            .map_err(|err| format!("arrow ipc create_or_open failed: {err:?}"))?;
        let signal = WindowsSignal::create_or_open(&config.signal_name)?;
        Ok(Self {
            rows: Vec::with_capacity(config.batch_max_rows),
            config,
            segment,
            signal,
            next_batch_id: 1,
        })
    }

    pub fn batch_interval_ms(&self) -> u64 {
        self.config.batch_interval_ms
    }

    pub fn signal_name(&self) -> &str {
        &self.config.signal_name
    }

    pub fn push_event(&mut self, event: ArrowMarketEvent) -> Result<Option<u64>, String> {
        self.rows.push(event);
        if self.rows.len() >= self.config.batch_max_rows {
            return self.flush();
        }
        Ok(None)
    }

    pub fn flush(&mut self) -> Result<Option<u64>, String> {
        if self.rows.is_empty() {
            return Ok(None);
        }
        let batch_id = self.next_batch_id;
        let batch = self.build_batch(batch_id)?;
        let payload = serialize_batch(&batch)?;
        self.segment.write_message(&payload)?;
        self.signal.signal()?;
        self.rows.clear();
        self.next_batch_id = self
            .next_batch_id
            .checked_add(1)
            .ok_or_else(|| "arrow batch id overflow".to_string())?;
        Ok(Some(batch_id))
    }

    fn build_batch(&self, batch_id: u64) -> Result<RecordBatch, String> {
        let symbols = self.rows.iter().map(|row| row.symbol.clone()).collect::<Vec<_>>();
        let seq_no = self.rows.iter().map(|row| row.seq_no).collect::<Vec<_>>();
        let event_type = self.rows.iter().map(|row| row.event_type).collect::<Vec<_>>();
        let trade_type = self.rows.iter().map(|row| row.trade_type.clone()).collect::<Vec<_>>();
        let trade_session = self.rows.iter().map(|row| row.trade_session.clone()).collect::<Vec<_>>();
        let bid = self.rows.iter().map(|row| row.bid).collect::<Vec<_>>();
        let ask = self.rows.iter().map(|row| row.ask).collect::<Vec<_>>();
        let last_price = self.rows.iter().map(|row| row.last_price).collect::<Vec<_>>();
        let volume = self.rows.iter().map(|row| row.volume).collect::<Vec<_>>();
        let bid_volume = self.rows.iter().map(|row| row.bid_volume).collect::<Vec<_>>();
        let ask_volume = self.rows.iter().map(|row| row.ask_volume).collect::<Vec<_>>();
        let current_volume = self.rows.iter().map(|row| row.current_volume).collect::<Vec<_>>();
        let turnover = self.rows.iter().map(|row| row.turnover).collect::<Vec<_>>();
        let current_turnover = self.rows.iter().map(|row| row.current_turnover).collect::<Vec<_>>();
        let impact_index = self.rows.iter().map(|row| row.impact_index).collect::<Vec<_>>();
        let is_sweep = self.rows.iter().map(|row| row.is_sweep).collect::<Vec<_>>();
        let arrival_mono_ns = self.rows.iter().map(|row| row.arrival_mono_ns).collect::<Vec<_>>();
        let batch_ids = vec![batch_id; self.rows.len()];

        let arrays: Vec<ArrayRef> = vec![
            Arc::new(StringArray::from(symbols)),
            Arc::new(UInt64Array::from(seq_no)),
            Arc::new(UInt8Array::from(event_type)),
            Arc::new(StringArray::from(trade_type)),
            Arc::new(StringArray::from(trade_session)),
            Arc::new(Float64Array::from(bid)),
            Arc::new(Float64Array::from(ask)),
            Arc::new(Float64Array::from(last_price)),
            Arc::new(UInt64Array::from(volume)),
            Arc::new(UInt64Array::from(bid_volume)),
            Arc::new(UInt64Array::from(ask_volume)),
            Arc::new(UInt64Array::from(current_volume)),
            Arc::new(Float64Array::from(turnover)),
            Arc::new(Float64Array::from(current_turnover)),
            Arc::new(Float64Array::from(impact_index)),
            Arc::new(BooleanArray::from(is_sweep)),
            Arc::new(UInt64Array::from(arrival_mono_ns)),
            Arc::new(UInt64Array::from(batch_ids)),
        ];
        RecordBatch::try_new(ARROW_IPC_SCHEMA.clone(), arrays)
            .map_err(|err| format!("arrow record batch build failed: {err}"))
    }
}

fn normalize_shm_capacity_bytes(value: usize) -> usize {
    if value <= DEFAULT_L0_IPC_SHM_BYTES {
        DEFAULT_ARROW_IPC_BYTES
    } else {
        value
    }
}

fn serialize_batch(batch: &RecordBatch) -> Result<Vec<u8>, String> {
    let mut cursor = Cursor::new(Vec::new());
    {
        let mut writer = StreamWriter::try_new(&mut cursor, &ARROW_IPC_SCHEMA)
            .map_err(|err| format!("arrow stream writer init failed: {err}"))?;
        writer
            .write(batch)
            .map_err(|err| format!("arrow stream writer write failed: {err}"))?;
        writer
            .finish()
            .map_err(|err| format!("arrow stream writer finish failed: {err}"))?;
    }
    Ok(cursor.into_inner())
}
