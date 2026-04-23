use crate::research_pending_labels::row_label_present;
use crate::research_store::ResearchFeatureStore;
use crate::research_store_build::feature_fields_only;
use crate::research_store_support::{l0_rust, parse_ts_any, project_allowed, VALID_INTERVALS};
use pyo3::{exceptions::PyValueError, prelude::*, types::PyDict, types::PyList};
use std::collections::HashMap;

impl ResearchFeatureStore {
    pub(crate) fn query_records(
        &self,
        py: Python<'_>,
        start_dt: chrono::DateTime<chrono::Utc>,
        end_dt: chrono::DateTime<chrono::Utc>,
        view: &str,
        fields: Option<Vec<String>>,
        interval: &str,
    ) -> PyResult<Vec<Py<PyAny>>> {
        let mut records = crate::research_store_io::load_range(py, &self.canonical_dir, "day", start_dt, end_dt)?;
        if view == "compact" {
            records = self.to_compact(py, records)?;
        } else {
            self.normalize_query_records(py, &records)?;
        }
        if let Some(field_list) = fields {
            records = self.project_fields(py, records, view, field_list)?;
        }
        self.apply_interval(py, records, interval)
    }

    pub(crate) fn to_compact(&self, py: Python<'_>, records: Vec<Py<PyAny>>) -> PyResult<Vec<Py<PyAny>>> {
        let native = l0_rust(py)?;
        records
            .into_iter()
            .map(|row| Ok(native.call_method1("service_research_to_compact_record", (row.bind(py),))?.unbind()))
            .collect()
    }

    pub(crate) fn project_fields(
        &self,
        py: Python<'_>,
        records: Vec<Py<PyAny>>,
        view: &str,
        fields: Vec<String>,
    ) -> PyResult<Vec<Py<PyAny>>> {
        if fields.len() > self.max_fields_per_query {
            return Err(PyValueError::new_err("too many fields requested"));
        }
        let native = l0_rust(py)?;
        let projected = native.call_method1(
            "service_research_project_records",
            (
                PyList::new(py, records.iter())?,
                fields,
                project_allowed(view),
                self.max_fields_per_query,
            ),
        )?;
        Ok(projected.downcast::<PyList>()?.iter().map(|row| row.unbind()).collect())
    }

    pub(crate) fn apply_interval(
        &self,
        py: Python<'_>,
        records: Vec<Py<PyAny>>,
        interval: &str,
    ) -> PyResult<Vec<Py<PyAny>>> {
        let step = VALID_INTERVALS
            .iter()
            .find(|(name, _)| *name == interval)
            .map(|(_, step)| *step)
            .unwrap_or(1);
        if step <= 1 {
            return Ok(records);
        }
        let native = l0_rust(py)?;
        let reduced = native.call_method1(
            "service_research_apply_interval",
            (PyList::new(py, records.iter())?, step),
        )?;
        Ok(reduced.downcast::<PyList>()?.iter().map(|row| row.unbind()).collect())
    }

    pub(crate) fn normalize_query_records(&self, py: Python<'_>, records: &[Py<PyAny>]) -> PyResult<()> {
        for row in records {
            let dict = row.bind(py).downcast::<PyDict>()?;
            if row_label_present(&dict)? {
                if let Some(value) = dict.get_item("label_stored_at")? {
                    dict.set_item("stored_at", value)?;
                }
            }
            let _ = dict.del_item("label_stored_at");
        }
        Ok(())
    }

    pub(crate) fn update_pending_labels(
        &mut self,
        py: Python<'_>,
        ts: chrono::DateTime<chrono::Utc>,
        spot: f64,
        day_rows: &mut [Py<PyAny>],
    ) -> PyResult<()> {
        let mut key_to_index = HashMap::new();
        for (index, row) in day_rows.iter().enumerate() {
            let dict = row.bind(py).downcast::<PyDict>()?;
            let row_ts = dict
                .get_item("data_timestamp")?
                .and_then(|value| parse_ts_any(&value).ok().flatten());
            let l0_version = dict.get_item("l0_version")?.and_then(|value| value.extract::<i64>().ok());
            let symbol = dict.get_item("symbol")?.and_then(|value| value.extract::<String>().ok());
            if let (Some(inner_ts), Some(inner_version), Some(inner_symbol)) = (row_ts, l0_version, symbol) {
                key_to_index.insert(crate::research_pending_labels::pending_key(inner_ts, inner_version, &inner_symbol), index);
            }
        }
        let mut done = Vec::new();
        for (key, state) in self.pending_labels.iter_mut() {
            state.advance(ts, spot);
            if state.matured(ts) {
                if let Some(index) = key_to_index.get(key) {
                    let row = day_rows[*index].bind(py).downcast::<PyDict>()?;
                    if !row_label_present(&row)? {
                        crate::research_pending_labels::apply_label_to_row(py, &day_rows[*index], state, ts)?;
                    }
                }
                done.push(key.clone());
            }
        }
        for key in done {
            self.pending_labels.remove(&key);
        }
        Ok(())
    }

    pub(crate) fn latest_feature_fields(py: Python<'_>) -> PyResult<Vec<String>> {
        feature_fields_only(py)
    }
}
