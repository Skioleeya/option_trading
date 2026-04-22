use pyo3::prelude::*;
use pyo3::types::PyAny;

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct FiniteValidator;
#[pymethods]
impl FiniteValidator {
    #[new] fn new() -> Self { Self }
    #[pyo3(signature = (value, field=""))]
    fn validate(&self, value: Option<&Bound<'_, PyAny>>, field: &str) -> PyResult<(bool, Option<String>)> {
        let Some(value) = value else { return Ok((true, None)); };
        match value.extract::<f64>() {
            Ok(v) if v.is_finite() => Ok((true, None)),
            Ok(v) => Ok((false, Some(format!("{}: non-finite value {}", field, v)))),
            Err(_) => Ok((false, Some(format!("{}: cannot convert value to float", field)))),
        }
    }
    #[pyo3(signature = (value, field=""))]
    fn __call__(&self, value: Option<&Bound<'_, PyAny>>, field: &str) -> PyResult<(bool, Option<String>)> { self.validate(value, field) }
}

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct PositiveValidator { #[pyo3(get, set)] allow_zero: bool }
#[pymethods]
impl PositiveValidator {
    #[new]
    #[pyo3(signature = (allow_zero=false))]
    fn new(allow_zero: bool) -> Self { Self { allow_zero } }
    #[pyo3(signature = (value, field=""))]
    fn validate(&self, value: Option<&Bound<'_, PyAny>>, field: &str) -> PyResult<(bool, Option<String>)> {
        let Some(value) = value else { return Ok((true, None)); };
        match value.extract::<f64>() {
            Ok(v) if self.allow_zero && v >= 0.0 => Ok((true, None)),
            Ok(v) if !self.allow_zero && v > 0.0 => Ok((true, None)),
            Ok(v) => Ok((false, Some(format!("{}: invalid positive value {}", field, v)))),
            Err(_) => Ok((false, Some(format!("{}: cannot convert value to float", field)))),
        }
    }
    #[pyo3(signature = (value, field=""))]
    fn __call__(&self, value: Option<&Bound<'_, PyAny>>, field: &str) -> PyResult<(bool, Option<String>)> { self.validate(value, field) }
}

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct RangeValidator { #[pyo3(get, set)] min_val: f64, #[pyo3(get, set)] max_val: f64 }
#[pymethods]
impl RangeValidator {
    #[new] fn new(min_val: f64, max_val: f64) -> Self { Self { min_val, max_val } }
    #[pyo3(signature = (value, field=""))]
    fn validate(&self, value: Option<&Bound<'_, PyAny>>, field: &str) -> PyResult<(bool, Option<String>)> {
        let Some(value) = value else { return Ok((true, None)); };
        match value.extract::<f64>() {
            Ok(v) if (self.min_val..=self.max_val).contains(&v) => Ok((true, None)),
            Ok(v) => Ok((false, Some(format!("{}: {} out of range [{}, {}]", field, v, self.min_val, self.max_val)))),
            Err(_) => Ok((false, Some(format!("{}: cannot convert value to float", field)))),
        }
    }
    #[pyo3(signature = (value, field=""))]
    fn __call__(&self, value: Option<&Bound<'_, PyAny>>, field: &str) -> PyResult<(bool, Option<String>)> { self.validate(value, field) }
}

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct ValidatorChain { validators: Vec<Py<PyAny>> }
#[pymethods]
impl ValidatorChain {
    #[new]
    #[pyo3(signature = (validators=None))]
    fn new(validators: Option<Vec<Py<PyAny>>>) -> Self { Self { validators: validators.unwrap_or_default() } }
    #[pyo3(signature = (value, field=""))]
    fn validate(&self, py: Python<'_>, value: Option<&Bound<'_, PyAny>>, field: &str) -> PyResult<(bool, Option<String>)> {
        for validator in &self.validators {
            let result = validator.bind(py).call_method1("validate", (value, field))?;
            let pair: (bool, Option<String>) = result.extract()?;
            if !pair.0 { return Ok(pair); }
        }
        Ok((true, None))
    }
    #[pyo3(signature = (validator))]
    fn append(&self, py: Python<'_>, validator: Py<PyAny>) -> Self {
        let mut validators = self.validators.iter().map(|v| v.clone_ref(py)).collect::<Vec<_>>();
        validators.push(validator);
        Self { validators }
    }
    #[pyo3(signature = (value, field=""))]
    fn __call__(&self, py: Python<'_>, value: Option<&Bound<'_, PyAny>>, field: &str) -> PyResult<(bool, Option<String>)> { self.validate(py, value, field) }
}

pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<FiniteValidator>()?;
    m.add_class::<PositiveValidator>()?;
    m.add_class::<RangeValidator>()?;
    m.add_class::<ValidatorChain>()?;
    Ok(())
}
