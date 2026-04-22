use crate::helpers::{
    clone_fields, clone_or_from_kwargs, get_attr, kwargs_to_fields, merge_fields, model_dump_fields,
    py_bool, py_dict, set_attr, FieldMap,
};
use crate::micro_state::MicroStructureAnalysis;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyType};

#[pyclass(module = "shared_rust.models")]
pub struct AgentB1Output {
    fields: FieldMap,
}

#[pymethods]
impl AgentB1Output {
    #[new]
    #[pyo3(signature = (**kwargs))]
    fn new(py: Python<'_>, kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<Self> {
        let mut fields = FieldMap::new();
        fields.insert("gamma_walls".into(), py_dict(py));
        fields.insert("gamma_flip".into(), py_bool(py, false)?);
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
            let mut fields = AgentB1Output::new(py, kwargs)?.fields;
            if let Some(value) = fields.get("micro_structure") {
                let bound = value.bind(py);
                if !bound.is_none() && bound.downcast::<PyDict>().is_ok() {
                    let cls = py.get_type::<MicroStructureAnalysis>();
                    let instance = cls.call_method1("model_validate", (bound.downcast::<PyDict>()?,))?;
                    fields.insert("micro_structure".into(), instance.unbind());
                }
            }
            Ok(Self { fields })
        })
    }
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<AgentB1Output>()?;
    Ok(())
}
