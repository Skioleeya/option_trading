use pyo3::prelude::*;

mod gateway_core;
mod gateway_rest;
mod helpers;
pub mod ipc;
mod rest_rows;
pub mod schema;
pub mod threat;

pub use gateway_core::RustIngestGateway;

#[pymodule]
fn l0_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustIngestGateway>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use crate::helpers::non_negative_volume_to_u64;

    #[test]
    fn non_negative_volume_clamps_negative_and_zero() {
        assert_eq!(non_negative_volume_to_u64(-1), 0);
        assert_eq!(non_negative_volume_to_u64(0), 0);
    }

    #[test]
    fn non_negative_volume_keeps_positive() {
        assert_eq!(non_negative_volume_to_u64(1), 1);
        assert_eq!(non_negative_volume_to_u64(123_456), 123_456);
    }
}
