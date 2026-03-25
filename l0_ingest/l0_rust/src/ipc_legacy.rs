use crate::schema::InstitutionalMarketEvent;
use crate::schema::{SHM_META_MAGIC, SHM_SCHEMA_VERSION};
use shared_memory::*;
#[cfg(windows)]
use std::ffi::c_void;
#[cfg(windows)]
use std::iter;
#[cfg(windows)]
use std::os::windows::ffi::OsStrExt;
#[cfg(windows)]
use std::ptr;
use std::sync::atomic::{AtomicU64, Ordering};

pub const BUFFER_SIZE: usize = 1024 * 1024; // 1M events
pub const IPC_HEADER_SIZE: usize = 128;
pub const IPC_HEAD_OFFSET: usize = 0;
pub const IPC_TAIL_OFFSET: usize = 64;
pub const IPC_BUFFER_OFFSET: usize = IPC_HEADER_SIZE;
pub const IPC_META_MAGIC_OFFSET: usize = 16;
pub const IPC_META_SCHEMA_VERSION_OFFSET: usize = 20;
pub const IPC_META_EVENT_SIZE_OFFSET: usize = 24;
pub const ARROW_IPC_LENGTH_OFFSET: usize = 0;
pub const DEFAULT_ARROW_IPC_BYTES: usize = 8 * 1024 * 1024;

#[allow(dead_code)]
pub struct IpcProducer {
    shm: Shmem,
    head: *mut AtomicU64,
    tail: *const AtomicU64,
    buffer: *mut InstitutionalMarketEvent,
}

unsafe impl Send for IpcProducer {}
unsafe impl Sync for IpcProducer {}

#[cfg(windows)]
type Handle = *mut c_void;

#[cfg(windows)]
const INVALID_HANDLE_VALUE: Handle = -1isize as Handle;
#[cfg(windows)]
const PAGE_READWRITE: u32 = 0x04;
#[cfg(windows)]
const FILE_MAP_ALL_ACCESS: u32 = 0xF001F;
#[cfg(all(test, windows))]
const FILE_MAP_READ: u32 = 0x0004;

#[cfg(windows)]
#[link(name = "kernel32")]
unsafe extern "system" {
    fn CreateFileMappingW(
        file: Handle,
        attributes: *const c_void,
        protect: u32,
        max_size_high: u32,
        max_size_low: u32,
        name: *const u16,
    ) -> Handle;
    fn MapViewOfFile(
        file_mapping: Handle,
        desired_access: u32,
        file_offset_high: u32,
        file_offset_low: u32,
        num_bytes_to_map: usize,
    ) -> *mut c_void;
    #[cfg(test)]
    fn OpenFileMappingW(desired_access: u32, inherit_handle: i32, name: *const u16) -> Handle;
    fn UnmapViewOfFile(base_address: *const c_void) -> i32;
    fn CloseHandle(handle: Handle) -> i32;
}

#[cfg(windows)]
pub struct ArrowIpcSegment {
    handle: Handle,
    view_ptr: *mut u8,
    capacity: usize,
}

#[cfg(windows)]
unsafe impl Send for ArrowIpcSegment {}
#[cfg(windows)]
unsafe impl Sync for ArrowIpcSegment {}

#[cfg(windows)]
impl Drop for ArrowIpcSegment {
    fn drop(&mut self) {
        if !self.view_ptr.is_null() {
            let _ = unsafe { UnmapViewOfFile(self.view_ptr as *const c_void) };
            self.view_ptr = ptr::null_mut();
        }
        if !self.handle.is_null() {
            let _ = unsafe { CloseHandle(self.handle) };
            self.handle = ptr::null_mut();
        }
    }
}

#[cfg(not(windows))]
pub struct ArrowIpcSegment {
    capacity: usize,
}

#[cfg(not(windows))]
unsafe impl Send for ArrowIpcSegment {}
#[cfg(not(windows))]
unsafe impl Sync for ArrowIpcSegment {}

#[allow(dead_code)]
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
        // This is a placeholder for the actual batching logic
        // In a real high-perf scenario, we would use pre-allocated buffers
        None
    }
}

impl ArrowIpcSegment {
    #[cfg(windows)]
    pub fn create_or_open(path: &str, capacity: usize) -> Result<Self, ShmemError> {
        let total_size = capacity + 4;
        let wide_name = to_wide(path);
        let max_size = total_size as u64;
        let handle = unsafe {
            CreateFileMappingW(
                INVALID_HANDLE_VALUE,
                ptr::null(),
                PAGE_READWRITE,
                (max_size >> 32) as u32,
                (max_size & 0xFFFF_FFFF) as u32,
                wide_name.as_ptr(),
            )
        };
        if handle.is_null() {
            let err = std::io::Error::last_os_error().raw_os_error().unwrap_or_default();
            return Err(ShmemError::MapCreateFailed(err as u32));
        }
        let view_ptr = unsafe { MapViewOfFile(handle, FILE_MAP_ALL_ACCESS, 0, 0, total_size) };
        if view_ptr.is_null() {
            let err = std::io::Error::last_os_error().raw_os_error().unwrap_or_default();
            unsafe {
                let _ = CloseHandle(handle);
            }
            return Err(ShmemError::MapOpenFailed(err as u32));
        }
        Ok(Self {
            handle,
            view_ptr: view_ptr as *mut u8,
            capacity,
        })
    }

    #[cfg(not(windows))]
    pub fn create_or_open(_path: &str, capacity: usize) -> Result<Self, ShmemError> {
        let _ = capacity;
        Err(ShmemError::UnknownOsError(0))
    }

    pub fn write_message(&mut self, payload: &[u8]) -> Result<(), String> {
        if payload.len() > self.capacity {
            return Err(format!(
                "arrow ipc payload too large: payload={} capacity={}",
                payload.len(),
                self.capacity
            ));
        }
        unsafe {
            if self.view_ptr.is_null() {
                return Err("arrow ipc shared memory base pointer is null".to_string());
            }
            let len_bytes = (payload.len() as u32).to_le_bytes();
            std::ptr::copy_nonoverlapping(
                len_bytes.as_ptr(),
                self.view_ptr.add(ARROW_IPC_LENGTH_OFFSET),
                len_bytes.len(),
            );
            std::ptr::copy_nonoverlapping(payload.as_ptr(), self.view_ptr.add(4), payload.len());
            if payload.len() < self.capacity {
                std::ptr::write_bytes(self.view_ptr.add(4 + payload.len()), 0, self.capacity - payload.len());
            }
        }
        Ok(())
    }
}

#[cfg(windows)]
fn to_wide(value: &str) -> Vec<u16> {
    std::ffi::OsStr::new(value)
        .encode_wide()
        .chain(iter::once(0))
        .collect()
}

#[cfg(all(test, windows))]
fn named_mapping_visible(path: &str) -> bool {
    let wide = to_wide(path);
    let handle = unsafe { OpenFileMappingW(FILE_MAP_READ, 0, wide.as_ptr()) };
    if handle.is_null() {
        return false;
    }
    let view = unsafe { MapViewOfFile(handle, FILE_MAP_READ, 0, 0, 0) };
    if view.is_null() {
        unsafe {
            let _ = CloseHandle(handle);
        }
        return false;
    }
    unsafe {
        let _ = UnmapViewOfFile(view);
        let _ = CloseHandle(handle);
    }
    true
}

#[cfg(all(test, windows))]
mod tests {
    use super::*;

    #[test]
    fn arrow_ipc_segment_exposes_named_mapping() {
        let name = format!("codex-arrow-ipc-{}", std::process::id());
        let _segment = ArrowIpcSegment::create_or_open(&name, 4096).expect("segment should create");
        assert!(named_mapping_visible(&name), "OpenFileMappingW should attach to named segment");
    }
}

unsafe fn write_header_metadata(base: *mut u8) {
    unsafe {
        write_u32_le(base, IPC_META_MAGIC_OFFSET, SHM_META_MAGIC);
        write_u32_le(base, IPC_META_SCHEMA_VERSION_OFFSET, SHM_SCHEMA_VERSION);
        write_u32_le(
            base,
            IPC_META_EVENT_SIZE_OFFSET,
            std::mem::size_of::<InstitutionalMarketEvent>() as u32,
        );
    }
}

unsafe fn write_u32_le(base: *mut u8, offset: usize, value: u32) {
    let bytes = value.to_le_bytes();
    unsafe {
        std::ptr::copy_nonoverlapping(bytes.as_ptr(), base.add(offset), bytes.len());
    }
}
