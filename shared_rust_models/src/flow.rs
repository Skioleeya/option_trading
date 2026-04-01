use crate::helpers::{
    clone_fields, clone_or_from_kwargs, finite_f64, get_attr, kwargs_to_fields, merge_fields,
    model_dump_fields, py_bool, py_f64, py_str, set_attr, FieldMap,
};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyType};

const FLOW_DIRECTION_VALUES: [&str; 3] = ["BULLISH", "BEARISH", "NEUTRAL"];
const FLOW_INTENSITY_VALUES: [&str; 4] = ["EXTREME", "HIGH", "MODERATE", "LOW"];

fn flow_defaults(py: Python<'_>) -> PyResult<FieldMap> {
    let mut fields = FieldMap::new();
    fields.insert("symbol".into(), py_str(py, "UNKNOWN")?);
    fields.insert("option_type".into(), py_str(py, "PUT")?);
    Ok(fields)
}

fn validate_flow_input(py: Python<'_>, fields: &FieldMap) -> PyResult<()> {
    for name in ["delta", "gamma", "vanna", "implied_volatility", "historical_volatility"] {
        finite_f64(fields, name, py)?;
    }
    Ok(())
}

fn flow_component_defaults(py: Python<'_>) -> PyResult<FieldMap> {
    let mut fields = FieldMap::new();
    fields.insert("is_valid".into(), py_bool(py, true)?);
    fields.insert("failure_reason".into(), py_str(py, "")?);
    Ok(fields)
}

fn flow_output_defaults(py: Python<'_>) -> PyResult<FieldMap> {
    let mut fields = FieldMap::new();
    fields.insert("flow_direction".into(), py_str(py, FLOW_DIRECTION_VALUES[2])?);
    fields.insert("flow_intensity".into(), py_str(py, FLOW_INTENSITY_VALUES[3])?);
    fields.insert("engine_d_active".into(), py_bool(py, true)?);
    fields.insert("engine_e_active".into(), py_bool(py, true)?);
    fields.insert("engine_g_active".into(), py_bool(py, true)?);
    Ok(fields)
}

macro_rules! define_model {
    ($name:ident, $defaults:expr, $validator:expr) => {
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
                ($validator)(py, &fields)?;
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
                ($validator)(py, &fields)?;
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
                    ($validator)(py, &fields)?;
                    Ok(Self { fields })
                })
            }
        }
    };
}

#[pyclass(module = "shared_rust.models")]
pub struct FlowComponentResult {
    fields: FieldMap,
}

impl FlowComponentResult {
    fn with_defaults(py: Python<'_>, mut fields: FieldMap) -> PyResult<Self> {
        if !fields.contains_key("is_valid") {
            fields.insert("is_valid".into(), py_bool(py, true)?);
        }
        if !fields.contains_key("failure_reason") {
            fields.insert("failure_reason".into(), py_str(py, "")?);
        }
        Ok(Self { fields })
    }
}

#[pymethods]
impl FlowComponentResult {
    #[new]
    #[pyo3(signature = (**kwargs))]
    fn new(py: Python<'_>, kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<Self> {
        let fields = kwargs_to_fields(py, kwargs)?;
        Self::with_defaults(py, fields)
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
        Self::with_defaults(py, fields)
    }

    #[classmethod]
    fn model_validate(
        _cls: &Bound<'_, PyType>,
        py: Python<'_>,
        data: &Bound<'_, PyAny>,
    ) -> PyResult<Self> {
        clone_or_from_kwargs(data, |py, kwargs| Self::new(py, kwargs))
    }
}

#[pyclass(module = "shared_rust.models")]
pub struct FlowEngineOutput {
    fields: FieldMap,
}

impl FlowEngineOutput {
    fn with_defaults(py: Python<'_>, mut fields: FieldMap) -> PyResult<Self> {
        if !fields.contains_key("flow_direction") {
            fields.insert("flow_direction".into(), py_str(py, FLOW_DIRECTION_VALUES[2])?);
        }
        if !fields.contains_key("flow_intensity") {
            fields.insert("flow_intensity".into(), py_str(py, FLOW_INTENSITY_VALUES[3])?);
        }
        if !fields.contains_key("engine_d_active") {
            fields.insert("engine_d_active".into(), py_bool(py, true)?);
        }
        if !fields.contains_key("engine_e_active") {
            fields.insert("engine_e_active".into(), py_bool(py, true)?);
        }
        if !fields.contains_key("engine_g_active") {
            fields.insert("engine_g_active".into(), py_bool(py, true)?);
        }
        Ok(Self { fields })
    }
}

#[pymethods]
impl FlowEngineOutput {
    #[new]
    #[pyo3(signature = (**kwargs))]
    fn new(py: Python<'_>, kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<Self> {
        let fields = kwargs_to_fields(py, kwargs)?;
        Self::with_defaults(py, fields)
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
        Self::with_defaults(py, fields)
    }

    #[classmethod]
    fn model_validate(
        _cls: &Bound<'_, PyType>,
        py: Python<'_>,
        data: &Bound<'_, PyAny>,
    ) -> PyResult<Self> {
        clone_or_from_kwargs(data, |py, kwargs| Self::new(py, kwargs))
    }
}

#[pyclass(module = "shared_rust.models")]
pub struct FlowEngineInput {
    fields: FieldMap,
}

impl FlowEngineInput {
    fn from_chain_entry_impl(py: Python<'_>, opt: &Bound<'_, PyDict>, spot: f64, atm_iv: f64) -> PyResult<Self> {
        let option_text = opt
            .get_item("option_type")?
            .map(|value| value.extract::<String>())
            .transpose()?
            .unwrap_or_else(|| "PUT".to_string())
            .to_uppercase();
        let option_type = if matches!(option_text.as_str(), "CALL" | "C") { "CALL" } else { "PUT" };
        let mut fields = flow_defaults(py)?;
        for (key, value) in [
            ("symbol", opt.get_item("symbol")?),
            ("strike", opt.get_item("strike")?),
            ("volume", opt.get_item("volume")?),
            ("turnover", opt.get_item("turnover")?),
            ("last_price", opt.get_item("last_price")?),
            ("implied_volatility", opt.get_item("implied_volatility")?),
            ("historical_volatility", opt.get_item("historical_volatility")?),
            ("open_interest", opt.get_item("open_interest")?),
            ("delta", opt.get_item("delta")?),
            ("gamma", opt.get_item("gamma")?),
            ("vanna", opt.get_item("vanna")?),
        ] {
            if let Some(value) = value {
                fields.insert(key.to_string(), value.unbind());
            }
        }
        fields.insert("option_type".into(), py_str(py, option_type)?);
        fields.insert("spot".into(), py_f64(py, spot)?);
        fields.insert("atm_iv".into(), py_f64(py, atm_iv)?);
        validate_flow_input(py, &fields)?;
        Ok(Self { fields })
    }
}

#[pymethods]
impl FlowEngineInput {
    #[new]
    #[pyo3(signature = (**kwargs))]
    fn new(py: Python<'_>, kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<Self> {
        let mut fields = flow_defaults(py)?;
        merge_fields(&mut fields, kwargs_to_fields(py, kwargs)?);
        validate_flow_input(py, &fields)?;
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
        validate_flow_input(py, &fields)?;
        Ok(Self { fields })
    }

    #[classmethod]
    fn model_validate(
        _cls: &Bound<'_, PyType>,
        py: Python<'_>,
        data: &Bound<'_, PyAny>,
    ) -> PyResult<Self> {
        clone_or_from_kwargs(data, |py, kwargs| {
            let mut fields = flow_defaults(py)?;
            merge_fields(&mut fields, kwargs_to_fields(py, kwargs)?);
            validate_flow_input(py, &fields)?;
            Ok(Self { fields })
        })
    }

    #[classmethod]
    fn from_chain_entry(
        _cls: &Bound<'_, PyType>,
        py: Python<'_>,
        opt: &Bound<'_, PyDict>,
        spot: f64,
        atm_iv: f64,
    ) -> PyResult<Self> {
        Self::from_chain_entry_impl(py, opt, spot, atm_iv)
    }
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<FlowEngineInput>()?;
    module.add_class::<FlowComponentResult>()?;
    module.add_class::<FlowEngineOutput>()?;
    Ok(())
}
