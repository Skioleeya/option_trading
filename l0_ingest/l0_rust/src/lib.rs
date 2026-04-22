use pyo3::prelude::*;

mod contract_metrics;
mod contract_option_chain;
mod arrow_ipc;
mod gateway_core;
mod gateway_event_map;
mod gateway_push_diag;
mod gateway_rest;
mod gateway_stress;
mod helpers;
pub mod ipc_legacy;
mod ipc_runtime;
mod ipc_writer;
mod l0_event_support;
mod l0_market_bridge;
mod l0_orchestration_support;
mod l0_poller_support;
mod l0_projection;
mod l0_sanitization;
mod l0_state_support;
mod l0_sync_support;
mod l0_subscription_support;
mod quote_contract_support;
mod quote_profile_support;
mod model_contracts;
mod research_store_runtime;
mod research_store_storage;
mod rest_rows;
pub mod schema;
mod sdk_config;
mod service_support;
mod tactical_triad_logic;
pub mod threat;
pub mod transport_contract;
mod windows_signal;

pub use gateway_core::RustIngestGateway;
pub use ipc_writer::ArrowBatchWriter;

#[pymodule]
fn l0_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustIngestGateway>()?;
    ipc_runtime::register(m)?;
    transport_contract::register(m)?;
    contract_metrics::register(m)?;
    contract_option_chain::register(m)?;
    l0_event_support::register(m)?;
    l0_market_bridge::register(m)?;
    l0_orchestration_support::register(m)?;
    l0_poller_support::register(m)?;
    l0_projection::register(m)?;
    l0_sanitization::register(m)?;
    l0_state_support::register(m)?;
    l0_sync_support::register(m)?;
    l0_subscription_support::register(m)?;
    quote_contract_support::register(m)?;
    quote_profile_support::register(m)?;
    gateway_push_diag::register(m)?;
    gateway_rest::register(m)?;
    model_contracts::register(m)?;
    research_store_runtime::register(m)?;
    research_store_storage::register(m)?;
    service_support::register(m)?;
    tactical_triad_logic::register(m)?;
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

#[cfg(test)]
mod arrow_ipc_tests;
