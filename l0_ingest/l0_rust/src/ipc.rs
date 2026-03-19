use std::sync::atomic::{AtomicU64, Ordering};
use shared_memory::*;
use crate::schema::InstitutionalMarketEvent;
use crate::schema::{SHM_META_MAGIC, SHM_SCHEMA_VERSION};

pub const BUFFER_SIZE: usize = 1024 * 1024; // 1M events
pub const IPC_HEADER_SIZE: usize = 128;
pub const IPC_HEAD_OFFSET: usize = 0;
pub const IPC_TAIL_OFFSET: usize = 64;
pub const IPC_BUFFER_OFFSET: usize = IPC_HEADER_SIZE;
pub const IPC_META_MAGIC_OFFSET: usize = 16;
pub const IPC_META_SCHEMA_VERSION_OFFSET: usize = 20;
pub const IPC_META_EVENT_SIZE_OFFSET: usize = 24;

pub struct IpcProducer {
    shm: Shmem,
    head: *mut AtomicU64,
    tail: *const AtomicU64,
    buffer: *mut InstitutionalMarketEvent,
}

unsafe impl Send for IpcProducer {}
unsafe impl Sync for IpcProducer {}

impl IpcProducer {
    pub fn new(path: &str) -> ShmemConf {
        ShmemConf::new()
            .size(BUFFER_SIZE * std::mem::size_of::<InstitutionalMarketEvent>() + IPC_HEADER_SIZE)
            .os_id(path)
    }

    pub fn from_shmem(shm: Shmem) -> Self {
        let base = shm.as_ptr() as *mut u8;
        unsafe {
            let head = base.add(IPC_HEAD_OFFSET) as *mut AtomicU64;
            let tail = base.add(IPC_TAIL_OFFSET) as *mut AtomicU64;
             
            // Initialization: Only if we are the owner or the memory is uninitialized
            // For safety in this high-perf design, we reset the control pointers
            (*head).store(0, Ordering::Release);
            (*tail).store(0, Ordering::Release);
            write_header_metadata(base);
             
            IpcProducer {
                shm,
                head,
                tail: tail as *const AtomicU64,
                buffer: base.add(IPC_BUFFER_OFFSET) as *mut InstitutionalMarketEvent,
            }
        }
    }

    pub fn push(&self, event: &InstitutionalMarketEvent) -> bool {
        let head = unsafe { (*self.head).load(Ordering::Acquire) };
        let tail = unsafe { (*self.tail).load(Ordering::Acquire) };

        if head + 1 == tail {
            return false; // Full
        }

        unsafe {
            let target = self.buffer.add((head % BUFFER_SIZE as u64) as usize);
            std::ptr::write(target, event.clone());
            (*self.head).store(head + 1, Ordering::Release);
        }
        true
    }

    pub fn to_record_batch(&self) -> Option<arrow::record_batch::RecordBatch> {
        use arrow::array::*;
        use crate::schema::MARKET_EVENT_SCHEMA;
        
        // This is a placeholder for the actual batching logic
        // In a real high-perf scenario, we would use pre-allocated buffers
        None
    }
}

unsafe fn write_header_metadata(base: *mut u8) {
    write_u32_le(base, IPC_META_MAGIC_OFFSET, SHM_META_MAGIC);
    write_u32_le(base, IPC_META_SCHEMA_VERSION_OFFSET, SHM_SCHEMA_VERSION);
    write_u32_le(
        base,
        IPC_META_EVENT_SIZE_OFFSET,
        std::mem::size_of::<InstitutionalMarketEvent>() as u32,
    );
}

unsafe fn write_u32_le(base: *mut u8, offset: usize, value: u32) {
    let bytes = value.to_le_bytes();
    std::ptr::copy_nonoverlapping(bytes.as_ptr(), base.add(offset), bytes.len());
}
