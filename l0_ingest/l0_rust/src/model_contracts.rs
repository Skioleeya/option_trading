use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyModule};

const FLOW_INPUT_FINITE_FIELDS: [&str; 5] = [
    "delta",
    "gamma",
    "vanna",
    "implied_volatility",
    "historical_volatility",
];
const FLOW_DIRECTION_VALUES: [&str; 3] = ["BULLISH", "BEARISH", "NEUTRAL"];
const FLOW_INTENSITY_VALUES: [&str; 4] = ["EXTREME", "HIGH", "MODERATE", "LOW"];

const GEX_REGIME_VALUES: [&str; 4] = ["SUPER_PIN", "DAMPING", "NEUTRAL", "ACCELERATION"];
const VANNA_FLOW_STATE_VALUES: [&str; 5] = [
    "DANGER_ZONE",
    "GRIND_STABLE",
    "NORMAL",
    "VANNA_FLIP",
    "UNAVAILABLE",
];
const VANNA_ACCELERATION_STATE_VALUES: [&str; 8] = [
    "ACCELERATING_FEAR",
    "DECELERATING_FEAR",
    "REVERSING_UP",
    "REVERSING_DOWN",
    "ACCELERATING_CALM",
    "DECELERATING_CALM",
    "STABLE",
    "UNAVAILABLE",
];
const IV_VELOCITY_STATE_VALUES: [&str; 8] = [
    "PAID_MOVE",
    "ORGANIC_GRIND",
    "HOLLOW_RISE",
    "HOLLOW_DROP",
    "PAID_DROP",
    "VOL_EXPANSION",
    "EXHAUSTION",
    "UNAVAILABLE",
];
const WALL_CALL_STATE_VALUES: [&str; 6] = [
    "RETREATING_RESISTANCE",
    "REINFORCED_WALL",
    "BREACHED",
    "DECAYING",
    "STABLE",
    "UNAVAILABLE",
];
const WALL_PUT_STATE_VALUES: [&str; 6] = [
    "RETREATING_SUPPORT",
    "REINFORCED_SUPPORT",
    "BREACHED",
    "DECAYING",
    "STABLE",
    "UNAVAILABLE",
];
const WALL_GAMMA_REGIME_VALUES: [&str; 3] = ["LONG_GAMMA", "SHORT_GAMMA", "NEUTRAL"];
const IV_REGIME_VALUES: [&str; 5] = ["LOW", "NORMAL", "ELEVATED", "HIGH", "EXTREME"];
const GEX_INTENSITY_VALUES: [&str; 6] = [
    "EXTREME_POSITIVE",
    "STRONG_POSITIVE",
    "MODERATE",
    "NEUTRAL",
    "STRONG_NEGATIVE",
    "EXTREME_NEGATIVE",
];

fn string_list<'py>(py: Python<'py>, values: &[&str]) -> PyResult<Bound<'py, PyList>> {
    let out = PyList::empty(py);
    for value in values {
        out.append(*value)?;
    }
    Ok(out)
}

fn build_flow_engine_spec(py: Python<'_>) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    out.set_item("_MODEL_VERSION", "1")?;
    out.set_item("finite_fields", string_list(py, &FLOW_INPUT_FINITE_FIELDS)?)?;
    out.set_item("flow_direction_values", string_list(py, &FLOW_DIRECTION_VALUES)?)?;
    out.set_item("flow_intensity_values", string_list(py, &FLOW_INTENSITY_VALUES)?)?;
    out.set_item("default_option_type", "PUT")?;
    out.set_item("default_symbol", "UNKNOWN")?;
    Ok(out.unbind())
}

fn add_numeric_default<'py>(
    py: Python<'py>,
    defaults: &Bound<'py, PyDict>,
    model_name: &str,
    string_rows: &[(&str, &str)],
    int_rows: &[(&str, i64)],
    float_rows: &[(&str, f64)],
    bool_rows: &[(&str, bool)],
) -> PyResult<()> {
    let row = PyDict::new(py);
    for (key, value) in string_rows {
        row.set_item(*key, *value)?;
    }
    for (key, value) in int_rows {
        row.set_item(*key, *value)?;
    }
    for (key, value) in float_rows {
        row.set_item(*key, *value)?;
    }
    for (key, value) in bool_rows {
        row.set_item(*key, *value)?;
    }
    defaults.set_item(model_name, row)?;
    Ok(())
}

fn build_microstructure_spec(py: Python<'_>) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    let enums = PyDict::new(py);
    enums.set_item("GexRegime", string_list(py, &GEX_REGIME_VALUES)?)?;
    enums.set_item("VannaFlowState", string_list(py, &VANNA_FLOW_STATE_VALUES)?)?;
    enums.set_item(
        "VannaAccelerationState",
        string_list(py, &VANNA_ACCELERATION_STATE_VALUES)?,
    )?;
    enums.set_item("IVVelocityState", string_list(py, &IV_VELOCITY_STATE_VALUES)?)?;
    enums.set_item(
        "WallMigrationCallState",
        string_list(py, &WALL_CALL_STATE_VALUES)?,
    )?;
    enums.set_item(
        "WallMigrationPutState",
        string_list(py, &WALL_PUT_STATE_VALUES)?,
    )?;
    enums.set_item("WallGammaRegime", string_list(py, &WALL_GAMMA_REGIME_VALUES)?)?;
    enums.set_item("IVRegime", string_list(py, &IV_REGIME_VALUES)?)?;
    enums.set_item("GexIntensity", string_list(py, &GEX_INTENSITY_VALUES)?)?;

    let defaults = PyDict::new(py);
    add_numeric_default(
        py,
        &defaults,
        "VIBTimeframeResult",
        &[("direction", "NEUTRAL")],
        &[("call_vol", 0), ("put_vol", 0)],
        &[("ratio", 0.0), ("confidence", 0.0)],
        &[],
    )?;
    add_numeric_default(
        py,
        &defaults,
        "VIBResult",
        &[("consensus", "NEUTRAL")],
        &[],
        &[("strength", 0.0), ("vol_accel_ratio", 1.0)],
        &[],
    )?;
    add_numeric_default(
        py,
        &defaults,
        "JumpResult",
        &[("direction", "NEUTRAL")],
        &[],
        &[("z_score", 0.0), ("magnitude_pct", 0.0)],
        &[("is_jump", false)],
    )?;
    add_numeric_default(
        py,
        &defaults,
        "WallContext",
        &[("gamma_regime", "NEUTRAL")],
        &[],
        &[
            ("hedge_flow_intensity", 0.0),
            ("counterfactual_vol_impact_bps", 0.0),
            ("near_wall_hedge_notional_m", 0.0),
            ("near_wall_liquidity", 0.0),
        ],
        &[],
    )?;
    add_numeric_default(
        py,
        &defaults,
        "VannaFlowResult",
        &[
            ("state", "UNAVAILABLE"),
            ("gex_regime", "NEUTRAL"),
            ("vanna_acceleration_state", "UNAVAILABLE"),
        ],
        &[("history_count", 0)],
        &[
            ("confidence", 0.0),
            ("wall_displacement_multiplier", 1.0),
            ("momentum_slope_multiplier", 1.0),
        ],
        &[],
    )?;
    add_numeric_default(
        py,
        &defaults,
        "IVVelocityResult",
        &[("state", "UNAVAILABLE")],
        &[],
        &[("confidence", 0.0), ("divergence_score", 0.0)],
        &[],
    )?;
    add_numeric_default(
        py,
        &defaults,
        "WallMigrationResult",
        &[("call_wall_state", "UNAVAILABLE"), ("put_wall_state", "UNAVAILABLE")],
        &[],
        &[("confidence", 0.0)],
        &[],
    )?;
    add_numeric_default(
        py,
        &defaults,
        "MicroStructureState",
        &[],
        &[],
        &[("avg_atm_vpin_score", 0.0)],
        &[("dealer_squeeze_alert", false)],
    )?;
    add_numeric_default(
        py,
        &defaults,
        "FusedSignalResult",
        &[("direction", "NEUTRAL"), ("regime", "UNKNOWN"), ("explanation", ""), ("iv_regime", "NORMAL"), ("gex_intensity", "NEUTRAL")],
        &[],
        &[("confidence", 0.0)],
        &[],
    )?;

    out.set_item("_MODEL_VERSION", "1")?;
    out.set_item("enums", enums)?;
    out.set_item("defaults", defaults)?;
    Ok(out.unbind())
}

fn build_agent_output_spec(py: Python<'_>) -> PyResult<Py<PyDict>> {
    let out = PyDict::new(py);
    let defaults = PyDict::new(py);
    defaults.set_item("gamma_flip", false)?;
    out.set_item("_MODEL_VERSION", "1")?;
    out.set_item("defaults", defaults)?;
    Ok(out.unbind())
}

#[pyfunction]
fn model_flow_engine_spec(py: Python<'_>) -> PyResult<Py<PyDict>> {
    build_flow_engine_spec(py)
}

#[pyfunction]
fn model_microstructure_spec(py: Python<'_>) -> PyResult<Py<PyDict>> {
    build_microstructure_spec(py)
}

#[pyfunction]
fn model_agent_output_spec(py: Python<'_>) -> PyResult<Py<PyDict>> {
    build_agent_output_spec(py)
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(model_flow_engine_spec, module)?)?;
    module.add_function(wrap_pyfunction!(model_microstructure_spec, module)?)?;
    module.add_function(wrap_pyfunction!(model_agent_output_spec, module)?)?;
    Ok(())
}
