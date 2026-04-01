use crate::helpers::{
    clone_fields, clone_or_from_kwargs, get_attr, kwargs_to_fields, merge_fields, model_dump_fields,
    py_bool, py_f64, py_i64, py_none, py_str, set_attr, FieldMap,
};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyType};

macro_rules! define_model {
    ($name:ident, $defaults:expr) => {
        #[pyclass(module = "shared_rust.models")]
        pub struct $name {
            fields: FieldMap,
        }

        #[pymethods]
        impl $name {
            #[new]
            #[pyo3(signature = (**kwargs))]
            fn new(py: Python<'_>, kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<Self> {
                let mut fields = ($defaults)(py)?;
                merge_fields(&mut fields, kwargs_to_fields(py, kwargs)?);
                Ok(Self { fields })
            }

            fn __getattr__(&self, py: Python<'_>, name: &str) -> PyResult<Py<PyAny>> {
                get_attr(py, &self.fields, name)
            }

            fn __setattr__(&mut self, name: &str, value: Py<PyAny>) {
                set_attr(&mut self.fields, name, value);
            }

            fn model_dump(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
                model_dump_fields(py, &self.fields)
            }

            #[pyo3(signature = (update=None))]
            fn model_copy(&self, py: Python<'_>, update: Option<&Bound<'_, PyDict>>) -> PyResult<Self> {
                let mut fields = clone_fields(py, &self.fields);
                merge_fields(&mut fields, kwargs_to_fields(py, update)?);
                Ok(Self { fields })
            }

            #[classmethod]
            fn model_validate(
                _cls: &Bound<'_, PyType>,
                py: Python<'_>,
                data: &Bound<'_, PyAny>,
            ) -> PyResult<Self> {
                clone_or_from_kwargs(data, |py, kwargs| {
                    let mut fields = ($defaults)(py)?;
                    merge_fields(&mut fields, kwargs_to_fields(py, kwargs)?);
                    Ok(Self { fields })
                })
            }
        }
    };
}

define_model!(
    VIBTimeframeResult,
    |py| -> PyResult<FieldMap> {
        let mut fields = FieldMap::new();
        fields.insert("ratio".into(), py_f64(py, 0.0)?);
        fields.insert("direction".into(), py_str(py, "NEUTRAL")?);
        fields.insert("confidence".into(), py_f64(py, 0.0)?);
        fields.insert("call_vol".into(), py_i64(py, 0)?);
        fields.insert("put_vol".into(), py_i64(py, 0)?);
        Ok(fields)
    }
);
define_model!(
    VIBResult,
    |py| -> PyResult<FieldMap> {
        let mut fields = FieldMap::new();
        fields.insert("tf_1m".into(), Py::new(py, VIBTimeframeResult::new(py, None)?)?.into_any());
        fields.insert("tf_5m".into(), Py::new(py, VIBTimeframeResult::new(py, None)?)?.into_any());
        fields.insert("tf_15m".into(), Py::new(py, VIBTimeframeResult::new(py, None)?)?.into_any());
        fields.insert("consensus".into(), py_str(py, "NEUTRAL")?);
        fields.insert("strength".into(), py_f64(py, 0.0)?);
        fields.insert("vol_accel_ratio".into(), py_f64(py, 1.0)?);
        Ok(fields)
    }
);
define_model!(
    JumpResult,
    |py| -> PyResult<FieldMap> {
        let mut fields = FieldMap::new();
        fields.insert("is_jump".into(), py_bool(py, false)?);
        fields.insert("z_score".into(), py_f64(py, 0.0)?);
        fields.insert("magnitude_pct".into(), py_f64(py, 0.0)?);
        fields.insert("direction".into(), py_str(py, "NEUTRAL")?);
        fields.insert("timestamp".into(), py_none(py));
        Ok(fields)
    }
);
define_model!(
    WallContext,
    |py| -> PyResult<FieldMap> {
        let mut fields = FieldMap::new();
        fields.insert("gamma_regime".into(), py_str(py, "NEUTRAL")?);
        for key in [
            "hedge_flow_intensity",
            "counterfactual_vol_impact_bps",
            "near_wall_hedge_notional_m",
            "near_wall_liquidity",
        ] {
            fields.insert(key.into(), py_f64(py, 0.0)?);
        }
        Ok(fields)
    }
);
define_model!(
    VannaFlowResult,
    |py| -> PyResult<FieldMap> {
        let mut fields = FieldMap::new();
        fields.insert("state".into(), py_str(py, "UNAVAILABLE")?);
        fields.insert("correlation".into(), py_none(py));
        fields.insert("gex_regime".into(), py_str(py, "NEUTRAL")?);
        fields.insert("net_gex".into(), py_none(py));
        fields.insert("confidence".into(), py_f64(py, 0.0)?);
        fields.insert("vanna_acceleration_state".into(), py_str(py, "UNAVAILABLE")?);
        for key in ["iv_roc", "iv_roc_prev", "iv_acceleration"] {
            fields.insert(key.into(), py_none(py));
        }
        fields.insert("history_count".into(), py_i64(py, 0)?);
        fields.insert("wall_displacement_multiplier".into(), py_f64(py, 1.0)?);
        fields.insert("momentum_slope_multiplier".into(), py_f64(py, 1.0)?);
        Ok(fields)
    }
);
define_model!(
    IVVelocityResult,
    |py| -> PyResult<FieldMap> {
        let mut fields = FieldMap::new();
        fields.insert("state".into(), py_str(py, "UNAVAILABLE")?);
        fields.insert("confidence".into(), py_f64(py, 0.0)?);
        fields.insert("iv_roc".into(), py_none(py));
        fields.insert("spot_roc".into(), py_none(py));
        fields.insert("divergence_score".into(), py_f64(py, 0.0)?);
        Ok(fields)
    }
);

pub fn register(py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    let _ = py;
    module.add_class::<VIBTimeframeResult>()?;
    module.add_class::<VIBResult>()?;
    module.add_class::<JumpResult>()?;
    module.add_class::<WallContext>()?;
    module.add_class::<VannaFlowResult>()?;
    module.add_class::<IVVelocityResult>()?;
    Ok(())
}
