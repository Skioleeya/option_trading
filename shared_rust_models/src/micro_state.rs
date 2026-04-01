use crate::helpers::{
    clone_fields, clone_or_from_kwargs, get_attr, kwargs_to_fields, merge_fields, model_dump_fields,
    py_bool, py_dict, py_f64, py_list, py_none, py_str, set_attr, FieldMap,
};
use crate::micro_core::{IVVelocityResult, JumpResult, VIBResult, VannaFlowResult, WallContext};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyType};
use pyo3::PyClass;

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
    WallMigrationResult,
    |py| -> PyResult<FieldMap> {
        let mut fields = FieldMap::new();
        fields.insert("call_wall_state".into(), py_str(py, "UNAVAILABLE")?);
        fields.insert("put_wall_state".into(), py_str(py, "UNAVAILABLE")?);
        fields.insert("confidence".into(), py_f64(py, 0.0)?);
        fields.insert("call_wall_delta".into(), py_none(py));
        fields.insert("put_wall_delta".into(), py_none(py));
        fields.insert("call_wall_history".into(), py_list(py));
        fields.insert("put_wall_history".into(), py_list(py));
        fields.insert("wall_context".into(), py_none(py));
        Ok(fields)
    }
);
define_model!(
    FusedSignalResult,
    |py| -> PyResult<FieldMap> {
        let mut fields = FieldMap::new();
        fields.insert("direction".into(), py_str(py, "NEUTRAL")?);
        fields.insert("confidence".into(), py_f64(py, 0.0)?);
        fields.insert("weights".into(), py_dict(py));
        fields.insert("regime".into(), py_str(py, "UNKNOWN")?);
        fields.insert("iv_regime".into(), py_str(py, "NORMAL")?);
        fields.insert("gex_intensity".into(), py_str(py, "NEUTRAL")?);
        fields.insert("explanation".into(), py_str(py, "")?);
        fields.insert("components".into(), py_dict(py));
        Ok(fields)
    }
);

fn micro_state_defaults(py: Python<'_>) -> PyResult<FieldMap> {
    let mut fields = FieldMap::new();
    for key in [
        "iv_velocity",
        "wall_migration",
        "vanna_flow_result",
        "vanna_flow",
        "volume_imbalance",
        "jump_detection",
        "wall_context",
    ] {
        fields.insert(key.into(), py_none(py));
    }
    fields.insert("mtf_consensus".into(), py_dict(py));
    fields.insert("dealer_squeeze_alert".into(), py_bool(py, false)?);
    fields.insert("avg_atm_vpin_score".into(), py_f64(py, 0.0)?);
    Ok(fields)
}

fn micro_analysis_defaults(py: Python<'_>) -> PyResult<FieldMap> {
    let mut fields = FieldMap::new();
    fields.insert("micro_structure_state".into(), py_none(py));
    Ok(fields)
}

fn coerce_field<T>(py: Python<'_>, fields: &mut FieldMap, key: &str) -> PyResult<()>
where
    T: PyClass,
{
    if let Some(value) = fields.get(key) {
        let bound = value.bind(py);
        if bound.is_none() {
            return Ok(());
        }
        if bound.hasattr("model_dump")? {
            fields.insert(key.to_string(), value.clone_ref(py));
            return Ok(());
        }
        if let Ok(mapping) = bound.downcast::<PyDict>() {
            let cls = py.get_type::<T>();
            let instance = cls.call_method1("model_validate", (mapping,))?;
            fields.insert(key.to_string(), instance.unbind());
        }
    }
    Ok(())
}

#[pyclass(module = "shared_rust.models")]
pub struct MicroStructureState {
    fields: FieldMap,
}

#[pymethods]
impl MicroStructureState {
    #[new]
    #[pyo3(signature = (**kwargs))]
    fn new(py: Python<'_>, kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<Self> {
        let mut fields = micro_state_defaults(py)?;
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
            let mut fields = MicroStructureState::new(py, kwargs)?.fields;
            coerce_field::<IVVelocityResult>(py, &mut fields, "iv_velocity")?;
            coerce_field::<WallMigrationResult>(py, &mut fields, "wall_migration")?;
            coerce_field::<VannaFlowResult>(py, &mut fields, "vanna_flow_result")?;
            coerce_field::<VannaFlowResult>(py, &mut fields, "vanna_flow")?;
            coerce_field::<VIBResult>(py, &mut fields, "volume_imbalance")?;
            coerce_field::<JumpResult>(py, &mut fields, "jump_detection")?;
            coerce_field::<WallContext>(py, &mut fields, "wall_context")?;
            Ok(Self { fields })
        })
    }
}

#[pyclass(module = "shared_rust.models")]
pub struct MicroStructureAnalysis {
    fields: FieldMap,
}

#[pymethods]
impl MicroStructureAnalysis {
    #[new]
    #[pyo3(signature = (**kwargs))]
    fn new(py: Python<'_>, kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<Self> {
        let mut fields = micro_analysis_defaults(py)?;
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
            let mut fields = MicroStructureAnalysis::new(py, kwargs)?.fields;
            coerce_field::<MicroStructureState>(py, &mut fields, "micro_structure_state")?;
            Ok(Self { fields })
        })
    }
}

pub fn register(py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    let _ = py;
    module.add_class::<WallMigrationResult>()?;
    module.add_class::<MicroStructureState>()?;
    module.add_class::<MicroStructureAnalysis>()?;
    module.add_class::<FusedSignalResult>()?;
    Ok(())
}
