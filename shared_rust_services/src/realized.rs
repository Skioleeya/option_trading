use pyo3::prelude::*;
use std::collections::VecDeque;

const TRADING_YEAR_SECONDS: f64 = 252.0 * 6.5 * 3600.0;

#[pyclass(get_all, module = "shared_rust.services")]
pub struct RealizedVolatilitySnapshot {
    realized_vol: f64,
    sample_count: usize,
    window_seconds: f64,
}

#[pyclass(module = "shared_rust.services")]
pub struct RollingRealizedVolatility {
    window_seconds: f64,
    annualization_seconds: f64,
    min_samples: usize,
    history: VecDeque<(f64, f64)>,
}

#[pymethods]
impl RollingRealizedVolatility {
    #[new]
    #[pyo3(signature = (window_seconds=900.0, annualization_seconds=TRADING_YEAR_SECONDS, min_samples=5))]
    fn new(window_seconds: f64, annualization_seconds: f64, min_samples: usize) -> Self {
        Self {
            window_seconds: window_seconds.max(1.0),
            annualization_seconds: annualization_seconds.max(1.0),
            min_samples: min_samples.max(2),
            history: VecDeque::with_capacity(10_000),
        }
    }

    fn update(&mut self, spot: f64, timestamp_mono: f64) -> RealizedVolatilitySnapshot {
        if !spot.is_finite() || spot <= 0.0 || !timestamp_mono.is_finite() {
            return RealizedVolatilitySnapshot {
                realized_vol: 0.0,
                sample_count: 0,
                window_seconds: self.window_seconds,
            };
        }
        self.history.push_back((timestamp_mono, spot));
        while self.history.len() > 10_000 {
            self.history.pop_front();
        }
        self.trim(timestamp_mono);
        RealizedVolatilitySnapshot {
            realized_vol: self.compute(),
            sample_count: self.history.len(),
            window_seconds: self.window_seconds,
        }
    }

    fn reset(&mut self) {
        self.history.clear();
    }
}

impl RollingRealizedVolatility {
    fn trim(&mut self, now_mono: f64) {
        let cutoff = now_mono - self.window_seconds;
        while let Some((ts, _)) = self.history.front() {
            if *ts >= cutoff {
                break;
            }
            self.history.pop_front();
        }
    }

    fn compute(&self) -> f64 {
        if self.history.len() < self.min_samples {
            return 0.0;
        }
        let mut log_returns = Vec::with_capacity(self.history.len().saturating_sub(1));
        let mut total_elapsed = 0.0;
        let mut prev = self.history[0];
        for current in self.history.iter().skip(1) {
            let dt = current.0 - prev.0;
            if dt > 0.0 && prev.1 > 0.0 && current.1 > 0.0 {
                log_returns.push((current.1 / prev.1).ln());
                total_elapsed += dt;
            }
            prev = *current;
        }
        if log_returns.len() + 1 < self.min_samples || total_elapsed <= 0.0 {
            return 0.0;
        }
        let mean = log_returns.iter().sum::<f64>() / log_returns.len() as f64;
        let variance = log_returns
            .iter()
            .map(|value| (value - mean).powi(2))
            .sum::<f64>()
            / (log_returns.len().saturating_sub(1).max(1) as f64);
        if !variance.is_finite() || variance <= 0.0 {
            return 0.0;
        }
        let avg_dt = total_elapsed / log_returns.len() as f64;
        if avg_dt <= 0.0 || !avg_dt.is_finite() {
            return 0.0;
        }
        let annualization_factor = self.annualization_seconds / avg_dt;
        if annualization_factor <= 0.0 || !annualization_factor.is_finite() {
            return 0.0;
        }
        let realized_vol = (variance * annualization_factor).sqrt();
        if realized_vol.is_finite() && realized_vol >= 0.0 {
            realized_vol
        } else {
            0.0
        }
    }
}

pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RealizedVolatilitySnapshot>()?;
    m.add_class::<RollingRealizedVolatility>()?;
    Ok(())
}
