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

pub const DEFAULT_ARROW_IPC_BYTES: usize = 8 * 1024 * 1024;
const DEFAULT_ARROW_SLOT_COUNT: usize = 32;
const HEADER_BYTES: usize = 24;
const SLOT_HEADER_BYTES: usize = 16;
const HEADER_MAGIC: u32 = 0x4152_5131; // "ARQ1"

#[cfg(windows)]
type Handle = *mut c_void;

#[cfg(windows)]
const INVALID_HANDLE_VALUE: Handle = -1isize as Handle;
#[cfg(windows)]
const PAGE_READWRITE: u32 = 0x04;
#[cfg(windows)]
const FILE_MAP_ALL_ACCESS: u32 = 0xF001F;
#[cfg(windows)]
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
    fn OpenFileMappingW(desired_access: u32, inherit_handle: i32, name: *const u16) -> Handle;
    fn UnmapViewOfFile(base_address: *const c_void) -> i32;
    fn CloseHandle(handle: Handle) -> i32;
}

#[derive(Clone, Copy)]
struct ArrowIpcLayout {
    slot_count: usize,
    slot_payload_bytes: usize,
    total_size: usize,
}

impl ArrowIpcLayout {
    fn from_payload_budget(payload_bytes: usize) -> Result<Self, String> {
        let slot_count = DEFAULT_ARROW_SLOT_COUNT;
        let overhead = HEADER_BYTES + (slot_count * SLOT_HEADER_BYTES);
        if payload_bytes <= overhead {
            return Err(format!(
                "arrow ipc payload budget too small: payload_bytes={} overhead={}",
                payload_bytes, overhead
            ));
        }
        let slot_payload_bytes = (payload_bytes - overhead) / slot_count;
        if slot_payload_bytes == 0 {
            return Err("arrow ipc slot payload bytes resolved to zero".to_string());
        }
        Ok(Self {
            slot_count,
            slot_payload_bytes,
            total_size: HEADER_BYTES + (slot_count * (SLOT_HEADER_BYTES + slot_payload_bytes)),
        })
    }

    fn oldest_available_seq(&self, writer_seq: u64) -> u64 {
        writer_seq.saturating_sub(self.slot_count as u64).saturating_add(1).max(1)
    }
}

#[derive(Default, Clone, Copy)]
pub struct ArrowIpcReadCursor {
    initialized: bool,
    next_seq: u64,
    reader_last_seq: u64,
    dropped_batches: u64,
    gap_count: u64,
}

impl ArrowIpcReadCursor {
    pub fn reader_last_seq(&self) -> u64 {
        self.reader_last_seq
    }

    pub fn dropped_batches(&self) -> u64 {
        self.dropped_batches
    }

    pub fn gap_count(&self) -> u64 {
        self.gap_count
    }
}

#[cfg(windows)]
pub struct ArrowIpcSegment {
    handle: Handle,
    view_ptr: *mut u8,
    layout: ArrowIpcLayout,
}

#[cfg(not(windows))]
pub struct ArrowIpcSegment {
    shm: Shmem,
    layout: ArrowIpcLayout,
}

unsafe impl Send for ArrowIpcSegment {}
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

impl ArrowIpcSegment {
    #[cfg(windows)]
    pub fn create_or_open(path: &str, payload_bytes: usize) -> Result<Self, String> {
        let layout = ArrowIpcLayout::from_payload_budget(payload_bytes)?;
        let wide_name = to_wide(path);
        let max_size = layout.total_size as u64;
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
            return Err(format!("Arrow IPC shared memory create failed: {} (winerr={})", path, err));
        }
        let view_ptr = unsafe { MapViewOfFile(handle, FILE_MAP_ALL_ACCESS, 0, 0, layout.total_size) };
        if view_ptr.is_null() {
            let err = std::io::Error::last_os_error().raw_os_error().unwrap_or_default();
            unsafe {
                let _ = CloseHandle(handle);
            }
            return Err(format!("Arrow IPC shared memory map-view failed: {} (winerr={})", path, err));
        }
        let mut segment = Self {
            handle,
            view_ptr: view_ptr as *mut u8,
            layout,
        };
        segment.initialize_writer_view();
        Ok(segment)
    }

    #[cfg(not(windows))]
    pub fn create_or_open(path: &str, payload_bytes: usize) -> Result<Self, String> {
        let layout = ArrowIpcLayout::from_payload_budget(payload_bytes)?;
        let shm = match ShmemConf::new().size(layout.total_size).os_id(path).create() {
            Ok(shm) => shm,
            Err(ShmemError::LinkExists) | Err(ShmemError::MappingIdExists) => {
                ShmemConf::new()
                    .size(layout.total_size)
                    .os_id(path)
                    .open()
                    .map_err(|err| format!("Arrow IPC shared memory open failed: {} ({err:?})", path))?
            }
            Err(err) => return Err(format!("Arrow IPC shared memory create failed: {} ({err:?})", path)),
        };
        let mut segment = Self { shm, layout };
        segment.initialize_writer_view();
        Ok(segment)
    }

    #[cfg(windows)]
    pub fn open_readonly(path: &str, payload_bytes: usize) -> Result<Self, String> {
        let layout = ArrowIpcLayout::from_payload_budget(payload_bytes)?;
        let wide_name = to_wide(path);
        let handle = unsafe { OpenFileMappingW(FILE_MAP_READ, 0, wide_name.as_ptr()) };
        if handle.is_null() {
            let err = std::io::Error::last_os_error().raw_os_error().unwrap_or_default();
            return Err(format!("Arrow IPC shared memory mapping is not available: {} (winerr={})", path, err));
        }
        let view_ptr = unsafe { MapViewOfFile(handle, FILE_MAP_READ, 0, 0, layout.total_size) };
        if view_ptr.is_null() {
            let err = std::io::Error::last_os_error().raw_os_error().unwrap_or_default();
            unsafe {
                let _ = CloseHandle(handle);
            }
            return Err(format!("Arrow IPC shared memory map-view failed: {} (winerr={})", path, err));
        }
        Ok(Self {
            handle,
            view_ptr: view_ptr as *mut u8,
            layout,
        })
    }

    #[cfg(not(windows))]
    pub fn open_readonly(path: &str, payload_bytes: usize) -> Result<Self, String> {
        let layout = ArrowIpcLayout::from_payload_budget(payload_bytes)?;
        let shm = ShmemConf::new()
            .size(layout.total_size)
            .os_id(path)
            .open()
            .map_err(|err| format!("Arrow IPC shared memory open failed: {} ({err:?})", path))?;
        Ok(Self { shm, layout })
    }

    pub fn write_message(&mut self, payload: &[u8]) -> Result<u64, String> {
        if payload.len() > self.layout.slot_payload_bytes {
            return Err(format!(
                "arrow ipc payload too large: payload={} slot_capacity={}",
                payload.len(),
                self.layout.slot_payload_bytes
            ));
        }
        let seq = self.load_writer_seq().saturating_add(1);
        let slot_index = ((seq - 1) as usize) % self.layout.slot_count;
        unsafe {
            let slot_ptr = self.slot_ptr(slot_index);
            write_u64(slot_ptr, 0);
            write_u32(slot_ptr.add(8), 0);
            std::ptr::copy_nonoverlapping(payload.as_ptr(), slot_ptr.add(SLOT_HEADER_BYTES), payload.len());
            write_u64(slot_ptr, seq);
            write_u32(slot_ptr.add(8), payload.len() as u32);
            (*self.writer_seq_ptr()).store(seq, Ordering::Release);
        }
        Ok(seq)
    }

    pub fn read_next_message(&self, cursor: &mut ArrowIpcReadCursor) -> Result<Option<Vec<u8>>, String> {
        let writer_seq = self.load_writer_seq();
        if writer_seq == 0 {
            return Ok(None);
        }
        if !cursor.initialized {
            cursor.initialized = true;
            cursor.next_seq = self.layout.oldest_available_seq(writer_seq);
        }
        let oldest = self.layout.oldest_available_seq(writer_seq);
        if cursor.next_seq < oldest {
            cursor.dropped_batches += oldest - cursor.next_seq;
            cursor.gap_count += 1;
            cursor.next_seq = oldest;
        }
        if cursor.next_seq > writer_seq {
            return Ok(None);
        }
        let slot_index = ((cursor.next_seq - 1) as usize) % self.layout.slot_count;
        unsafe {
            let slot_ptr = self.slot_ptr(slot_index);
            let seq = read_u64(slot_ptr);
            let len = read_u32(slot_ptr.add(8)) as usize;
            if seq != cursor.next_seq || len == 0 {
                return Ok(None);
            }
            if len > self.layout.slot_payload_bytes {
                return Err(format!(
                    "Arrow IPC slot payload exceeds slot capacity: payload={} slot_capacity={}",
                    len, self.layout.slot_payload_bytes
                ));
            }
            let payload = std::slice::from_raw_parts(slot_ptr.add(SLOT_HEADER_BYTES), len).to_vec();
            let confirm_seq = read_u64(slot_ptr);
            let confirm_len = read_u32(slot_ptr.add(8)) as usize;
            if confirm_seq != seq || confirm_len != len {
                return Ok(None);
            }
            cursor.reader_last_seq = cursor.next_seq;
            cursor.next_seq = cursor.next_seq.saturating_add(1);
            Ok(Some(payload))
        }
    }

    pub fn diagnostics(&self, cursor: &ArrowIpcReadCursor) -> ArrowIpcReaderDiagnostics {
        let writer_batch_id = self.load_writer_seq();
        ArrowIpcReaderDiagnostics {
            writer_batch_id,
            reader_last_batch_id: cursor.reader_last_seq(),
            queued_batch_count: writer_batch_id.saturating_sub(cursor.reader_last_seq()),
            dropped_batch_count: cursor.dropped_batches(),
            reader_gap_count: cursor.gap_count(),
        }
    }

    fn load_writer_seq(&self) -> u64 {
        unsafe { (*self.writer_seq_ptr()).load(Ordering::Acquire) }
    }

    fn initialize_writer_view(&mut self) {
        unsafe {
            let base = self.base_ptr();
            std::ptr::write_bytes(base, 0, self.layout.total_size);
            write_u32(base.add(8), HEADER_MAGIC);
            write_u32(base.add(12), self.layout.slot_count as u32);
            write_u32(base.add(16), self.layout.slot_payload_bytes as u32);
        }
    }

    unsafe fn writer_seq_ptr(&self) -> *mut AtomicU64 {
        unsafe { self.base_ptr() as *mut AtomicU64 }
    }

    unsafe fn slot_ptr(&self, slot_index: usize) -> *mut u8 {
        unsafe {
            self.base_ptr()
                .add(HEADER_BYTES + (slot_index * (SLOT_HEADER_BYTES + self.layout.slot_payload_bytes)))
        }
    }

    unsafe fn base_ptr(&self) -> *mut u8 {
        #[cfg(windows)]
        {
            self.view_ptr
        }
        #[cfg(not(windows))]
        {
            self.shm.as_ptr() as *mut u8
        }
    }
}

pub struct ArrowIpcReaderDiagnostics {
    pub writer_batch_id: u64,
    pub reader_last_batch_id: u64,
    pub queued_batch_count: u64,
    pub dropped_batch_count: u64,
    pub reader_gap_count: u64,
}

unsafe fn write_u64(ptr: *mut u8, value: u64) {
    unsafe {
        std::ptr::copy_nonoverlapping(value.to_le_bytes().as_ptr(), ptr, 8);
    }
}

unsafe fn write_u32(ptr: *mut u8, value: u32) {
    unsafe {
        std::ptr::copy_nonoverlapping(value.to_le_bytes().as_ptr(), ptr, 4);
    }
}

unsafe fn read_u64(ptr: *mut u8) -> u64 {
    let bytes = unsafe { std::slice::from_raw_parts(ptr, 8) };
    u64::from_le_bytes(bytes.try_into().unwrap_or([0; 8]))
}

unsafe fn read_u32(ptr: *mut u8) -> u32 {
    let bytes = unsafe { std::slice::from_raw_parts(ptr, 4) };
    u32::from_le_bytes(bytes.try_into().unwrap_or([0; 4]))
}

#[cfg(windows)]
fn to_wide(value: &str) -> Vec<u16> {
    std::ffi::OsStr::new(value)
        .encode_wide()
        .chain(iter::once(0))
        .collect()
}
