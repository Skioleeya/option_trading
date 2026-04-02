use numpy::IntoPyArray;
use numpy::PyReadonlyArray1;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};

const SQRT_2PI: f64 = 2.506_628_274_631_000_2;
const INV_SQRT_2: f64 = 0.707_106_781_186_547_5;
const IV_FLOOR: f64 = 1e-8;
const POSITIVE_FLOOR: f64 = 1e-8;

fn norm_pdf(x: f64) -> f64 {
    (-0.5 * x * x).exp() / SQRT_2PI
}

fn norm_cdf(x: f64) -> f64 {
    0.5 * (1.0 + libm::erf(x * INV_SQRT_2))
}

#[pyfunction]
#[pyo3(signature = (spots, strikes, ivs, t_years, is_call, r=0.05, q=0.0))]
fn bsm_batch_numpy_tier<'py>(
    py: Python<'py>,
    spots: PyReadonlyArray1<'py, f64>,
    strikes: PyReadonlyArray1<'py, f64>,
    ivs: PyReadonlyArray1<'py, f64>,
    t_years: f64,
    is_call: PyReadonlyArray1<'py, bool>,
    r: f64,
    q: f64,
) -> PyResult<Py<PyDict>> {
    let spots_v = spots.as_array();
    let strikes_v = strikes.as_array();
    let ivs_v = ivs.as_array();
    let is_call_v = is_call.as_array();
    let n = spots_v.len();
    if strikes_v.len() != n || ivs_v.len() != n || is_call_v.len() != n {
        return Err(PyValueError::new_err(
            "bsm_batch_numpy_tier requires equal-length input arrays",
        ));
    }

    let mut delta = vec![0.0; n];
    let mut gamma = vec![0.0; n];
    let mut vega = vec![0.0; n];
    let mut vanna = vec![0.0; n];
    let mut charm = vec![0.0; n];
    let mut theta = vec![0.0; n];

    if !t_years.is_finite() || t_years <= 0.0 {
        let out = PyDict::new(py);
        out.set_item("delta", delta.into_pyarray(py))?;
        out.set_item("gamma", gamma.into_pyarray(py))?;
        out.set_item("vega", vega.into_pyarray(py))?;
        out.set_item("vanna", vanna.into_pyarray(py))?;
        out.set_item("charm", charm.into_pyarray(py))?;
        out.set_item("theta", theta.into_pyarray(py))?;
        return Ok(out.unbind());
    }

    let sqrt_t = t_years.sqrt();
    let eq_t = (-q * t_years).exp();
    let er_t = (-r * t_years).exp();

    for i in 0..n {
        let s = spots_v[i];
        let k = strikes_v[i];
        let iv = ivs_v[i];
        let call = is_call_v[i];

        if !s.is_finite() || !k.is_finite() || !iv.is_finite() || s <= 0.0 || k <= 0.0 || iv <= 0.0 {
            continue;
        }

        let safe_s = s.max(POSITIVE_FLOOR);
        let safe_k = k.max(POSITIVE_FLOOR);
        let safe_iv = iv.max(IV_FLOOR);
        let iv_sqrt_t = safe_iv * sqrt_t;
        let d1 = ((safe_s / safe_k).ln() + (r - q + 0.5 * safe_iv * safe_iv) * t_years) / iv_sqrt_t;
        let d2 = d1 - iv_sqrt_t;

        let nd1 = norm_pdf(d1);
        let cdf_d1 = norm_cdf(d1);
        let cdf_nd1 = norm_cdf(-d1);
        let cdf_d2 = norm_cdf(d2);
        let cdf_nd2 = norm_cdf(-d2);

        delta[i] = if call { eq_t * cdf_d1 } else { -eq_t * cdf_nd1 };
        gamma[i] = eq_t * nd1 / (safe_s * safe_iv * sqrt_t);
        vega[i] = safe_s * eq_t * nd1 * sqrt_t * 0.01;
        vanna[i] = -eq_t * nd1 * d2 / safe_iv * 0.01;

        let charm_num = 2.0 * (r - q) * t_years - d2 * safe_iv * sqrt_t;
        let charm_den = (2.0 * t_years * safe_iv * sqrt_t).max(1e-12);
        let charm_call = (q * eq_t * cdf_d1 - eq_t * nd1 * charm_num / charm_den) / 365.0;
        let charm_put = (-q * eq_t * cdf_nd1 - eq_t * nd1 * charm_num / charm_den) / 365.0;
        charm[i] = if call { charm_call } else { charm_put };

        let theta_call = (-(safe_s * safe_iv * eq_t * nd1) / (2.0 * sqrt_t)
            - r * safe_k * er_t * cdf_d2
            + q * safe_s * eq_t * cdf_d1)
            / 365.0;
        let theta_put = (-(safe_s * safe_iv * eq_t * nd1) / (2.0 * sqrt_t)
            + r * safe_k * er_t * cdf_nd2
            - q * safe_s * eq_t * cdf_nd1)
            / 365.0;
        theta[i] = if call { theta_call } else { theta_put };
    }

    let out = PyDict::new(py);
    out.set_item("delta", delta.into_pyarray(py))?;
    out.set_item("gamma", gamma.into_pyarray(py))?;
    out.set_item("vega", vega.into_pyarray(py))?;
    out.set_item("vanna", vanna.into_pyarray(py))?;
    out.set_item("charm", charm.into_pyarray(py))?;
    out.set_item("theta", theta.into_pyarray(py))?;
    Ok(out.unbind())
}

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(bsm_batch_numpy_tier, module)?)?;
    Ok(())
}
