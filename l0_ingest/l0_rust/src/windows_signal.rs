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

    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn CreateEventW(
            event_attributes: *const c_void,
            manual_reset: Bool,
            initial_state: Bool,
            name: Pcwstr,
        ) -> Handle;
        fn SetEvent(handle: Handle) -> Bool;
        fn CloseHandle(handle: Handle) -> Bool;
    }

    pub struct WindowsSignal {
        handle: Handle,
        name: String,
    }

    // Win32 event handles are process-owned kernel objects and may be signaled
    // from worker threads as long as this wrapper keeps sole drop ownership.
    unsafe impl Send for WindowsSignal {}

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

        pub fn signal(&self) -> Result<(), String> {
            let ok = unsafe { SetEvent(self.handle) };
            if ok == FALSE {
                return Err(format!("SetEvent failed for signal '{}'", self.name));
            }
            Ok(())
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
    pub struct WindowsSignal;

    impl WindowsSignal {
        pub fn create_or_open(name: &str) -> Result<Self, String> {
            Err(format!(
                "Windows named-event signal is unavailable on this platform: '{}'",
                name
            ))
        }

        pub fn signal(&self) -> Result<(), String> {
            Err("Windows named-event signal is unavailable on this platform".to_string())
        }
    }
}

pub use imp::WindowsSignal;
