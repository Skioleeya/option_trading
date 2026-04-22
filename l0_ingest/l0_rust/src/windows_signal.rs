#[cfg(windows)]
mod imp {
    use std::ffi::c_void;
    use std::iter;
    use std::os::windows::ffi::OsStrExt;
    use std::ptr;

    type Handle = *mut c_void;
    type Bool = i32;
    type Pcwstr = *const u16;

    const FALSE: Bool = 0;
    const EVENT_MODIFY_STATE: u32 = 0x0002;
    const SYNCHRONIZE: u32 = 0x0010_0000;
    const WAIT_OBJECT_0: u32 = 0;
    const WAIT_FAILED: u32 = 0xFFFF_FFFF;
    const INFINITE: u32 = 0xFFFF_FFFF;

    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn CreateEventW(
            event_attributes: *const c_void,
            manual_reset: Bool,
            initial_state: Bool,
            name: Pcwstr,
        ) -> Handle;
        fn OpenEventW(desired_access: u32, inherit_handle: Bool, name: Pcwstr) -> Handle;
        fn SetEvent(handle: Handle) -> Bool;
        fn WaitForSingleObject(handle: Handle, milliseconds: u32) -> u32;
        fn CloseHandle(handle: Handle) -> Bool;
    }

    pub struct WindowsSignal {
        handle: Handle,
        name: String,
    }

    // Win32 event handles are process-owned kernel objects and may be signaled
    // from worker threads as long as this wrapper keeps sole drop ownership.
    unsafe impl Send for WindowsSignal {}
    unsafe impl Sync for WindowsSignal {}

    impl WindowsSignal {
        pub fn create_or_open(name: &str) -> Result<Self, String> {
            let wide = to_wide(name);
            let handle = unsafe { CreateEventW(ptr::null(), FALSE, FALSE, wide.as_ptr()) };
            if handle.is_null() {
                return Err(format!("CreateEventW failed for signal '{}'", name));
            }
            Ok(Self {
                handle,
                name: name.to_string(),
            })
        }

        pub fn connect(name: &str) -> Result<Self, String> {
            let wide = to_wide(name);
            let mut handle = unsafe { OpenEventW(EVENT_MODIFY_STATE | SYNCHRONIZE, FALSE, wide.as_ptr()) };
            if handle.is_null() {
                handle = unsafe { CreateEventW(ptr::null(), FALSE, FALSE, wide.as_ptr()) };
            }
            if handle.is_null() {
                return Err(format!("failed to open or create Windows signal event '{}'", name));
            }
            Ok(Self {
                handle,
                name: name.to_string(),
            })
        }

        pub fn signal(&self) -> Result<(), String> {
            let ok = unsafe { SetEvent(self.handle) };
            if ok == FALSE {
                return Err(format!("SetEvent failed for signal '{}'", self.name));
            }
            Ok(())
        }

        pub fn wait(&self) -> Result<(), String> {
            let result = unsafe { WaitForSingleObject(self.handle, INFINITE) };
            if result == WAIT_OBJECT_0 {
                return Ok(());
            }
            if result == WAIT_FAILED {
                return Err(format!("WaitForSingleObject failed for signal '{}'", self.name));
            }
            Err(format!(
                "unexpected WaitForSingleObject result for signal '{}': {}",
                self.name, result
            ))
        }
    }

    impl Drop for WindowsSignal {
        fn drop(&mut self) {
            if !self.handle.is_null() {
                let _ = unsafe { CloseHandle(self.handle) };
            }
        }
    }

    fn to_wide(value: &str) -> Vec<u16> {
        std::ffi::OsStr::new(value)
            .encode_wide()
            .chain(iter::once(0))
            .collect()
    }
}

#[cfg(not(windows))]
mod imp {
    use std::time::Duration;

    pub struct WindowsSignal {
        _name: String,
    }

    impl WindowsSignal {
        pub fn create_or_open(name: &str) -> Result<Self, String> {
            if name.trim().is_empty() {
                return Err("signal name is required".to_string());
            }
            Ok(Self {
                _name: name.to_string(),
            })
        }

        pub fn connect(name: &str) -> Result<Self, String> {
            Self::create_or_open(name)
        }

        pub fn signal(&self) -> Result<(), String> {
            Ok(())
        }

        pub fn wait(&self) -> Result<(), String> {
            std::thread::sleep(Duration::from_millis(1));
            Ok(())
        }
    }
}

pub use imp::WindowsSignal;
