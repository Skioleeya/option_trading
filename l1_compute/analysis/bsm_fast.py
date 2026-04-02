"""BSM fast path with 3-tier compute routing (CuPy -> Numba -> NumPy/Rust)."""

from __future__ import annotations

import logging
import math
import time

import numpy as np
from l1_compute.aggregation.rust_bridge import rust_aggregate_from_greeks, rust_select_walls
from l1_compute.analysis.bsm_rust_bridge import rust_bsm_batch_numpy_tier

logger = logging.getLogger(__name__)
_GEX_SCALE_MILLION = 1_000_000.0

try:
    import cupy as cp  # type: ignore
    _gpu_arr = cp.array([1.0], dtype=cp.float64)  # force device init
    del _gpu_arr
    _CUPY_AVAILABLE = True
    logger.info("[bsm_fast] CuPy/CUDA detected — GPU engine is ACTIVE (Tier 1).")
except (ImportError, AttributeError, OSError, RuntimeError, ValueError):
    _CUPY_AVAILABLE = False
    logger.info(
        "[bsm_fast] CuPy not available — install `cupy-cuda12x` for GPU acceleration."
    )
try:
    from numba import njit, prange  # type: ignore
    _NUMBA_AVAILABLE = True
    logger.info("[bsm_fast] Numba detected — JIT engine enabled (Tier 2).")
except ImportError:
    _NUMBA_AVAILABLE = False
    logger.warning(
        "[bsm_fast] Numba not installed — falling back to NumPy vectorization (Tier 3). "
        "Run `pip install numba` for CPU-parallel performance."
    )

if _NUMBA_AVAILABLE:
    @njit(parallel=True, fastmath=True, cache=True)
    def _bsm_batch_numba(
        spots:    np.ndarray,   # float64[n]
        strikes:  np.ndarray,   # float64[n]
        ivs:      np.ndarray,   # float64[n]
        t_years:  float,
        is_call:  np.ndarray,   # bool[n]
        r:        float,
        q:        float,
    ):
        """
        Numba JIT - parallel batch BSM Greeks.
        Returns 6 flat arrays: delta, gamma, vega, vanna, charm, theta.
        """
        n = len(spots)
        delta_arr = np.empty(n, dtype=np.float64)
        gamma_arr = np.empty(n, dtype=np.float64)
        vega_arr  = np.empty(n, dtype=np.float64)
        vanna_arr = np.empty(n, dtype=np.float64)
        charm_arr = np.empty(n, dtype=np.float64)
        theta_arr = np.empty(n, dtype=np.float64)

        sqrt_t = math.sqrt(t_years)
        eq_t   = math.exp(-q * t_years)
        er_t   = math.exp(-r * t_years)
        _SQRT2    = math.sqrt(2.0)
        _SQRT2PI  = math.sqrt(2.0 * math.pi)
        _INV365   = 1.0 / 365.0

        for i in prange(n):  # parallel over contracts
            S  = spots[i]
            K  = strikes[i]
            iv = ivs[i]

            if iv <= 0.0 or S <= 0.0 or K <= 0.0 or t_years <= 0.0:
                delta_arr[i] = 0.0
                gamma_arr[i] = 0.0
                vega_arr[i]  = 0.0
                vanna_arr[i] = 0.0
                charm_arr[i] = 0.0
                theta_arr[i] = 0.0
                continue

            iv_sqrt_t = iv * sqrt_t
            d1 = (math.log(S / K) + (r - q + 0.5 * iv * iv) * t_years) / iv_sqrt_t
            d2 = d1 - iv_sqrt_t

            # norm_pdf(d1)
            nd1 = math.exp(-0.5 * d1 * d1) / _SQRT2PI
            # norm_cdf via erf
            cdf_d1  = 0.5 * (1.0 + math.erf( d1 / _SQRT2))
            cdf_nd1 = 0.5 * (1.0 + math.erf(-d1 / _SQRT2))
            cdf_d2  = 0.5 * (1.0 + math.erf( d2 / _SQRT2))
            cdf_nd2 = 0.5 * (1.0 + math.erf(-d2 / _SQRT2))

            if is_call[i]:
                delta_arr[i] = eq_t * cdf_d1
                theta = (
                    -(S * iv * eq_t * nd1) / (2.0 * sqrt_t)
                    - r * K * er_t * cdf_d2
                    + q * S * eq_t * cdf_d1
                )
                charm = (
                    q * eq_t * cdf_d1
                    - eq_t * nd1 * (2.0 * (r - q) * t_years - d2 * iv_sqrt_t)
                    / (2.0 * t_years * iv_sqrt_t)
                )
            else:
                delta_arr[i] = -eq_t * cdf_nd1
                theta = (
                    -(S * iv * eq_t * nd1) / (2.0 * sqrt_t)
                    + r * K * er_t * cdf_nd2
                    - q * S * eq_t * cdf_nd1
                )
                charm = (
                    -q * eq_t * cdf_nd1
                    - eq_t * nd1 * (2.0 * (r - q) * t_years - d2 * iv_sqrt_t)
                    / (2.0 * t_years * iv_sqrt_t)
                )

            gamma_arr[i] = eq_t * nd1 / (S * iv * sqrt_t)
            vega_arr[i]  = S * eq_t * nd1 * sqrt_t * 0.01
            vanna_arr[i] = -eq_t * nd1 * d2 / iv * 0.01
            charm_arr[i] = charm * _INV365
            theta_arr[i] = theta * _INV365

        return delta_arr, gamma_arr, vega_arr, vanna_arr, charm_arr, theta_arr

def _bsm_batch_numpy(
    spots:   np.ndarray,
    strikes: np.ndarray,
    ivs:     np.ndarray,
    t_years: float,
    is_call: np.ndarray,
    r: float,
    q: float,
) -> dict[str, np.ndarray]:
    """Rust-only Tier-3 path (legacy NumPy tier entrypoint)."""
    return rust_bsm_batch_numpy_tier(
        spots=spots,
        strikes=strikes,
        ivs=ivs,
        t_years=t_years,
        is_call=is_call,
        r=r,
        q=q,
    )

def _bsm_batch_cupy(
    spots:   np.ndarray,
    strikes: np.ndarray,
    ivs:     np.ndarray,
    t_years: float,
    is_call: np.ndarray,
    r: float,
    q: float,
    ois:     np.ndarray | None = None,
    mults:   np.ndarray | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, float] | None]:
    """GPU-accelerated BSM Greeks using CuPy CUDA element-wise ops.

    All arrays are transferred to device once, computed in parallel across
    the CUDA cores, then returned to CPU as NumPy arrays. For chain sizes
    n > 50 this outperforms Numba on CPU.
    """
    import cupy as cp  # already verified available
    import cupyx.scipy.special as scp

    cp_spots   = cp.asarray(spots.astype(np.float64))
    cp_strikes = cp.asarray(strikes.astype(np.float64))
    cp_ivs     = cp.asarray(ivs.astype(np.float64))
    cp_is_call = cp.asarray(is_call.astype(np.bool_))

    sqrt_t = math.sqrt(t_years) if t_years > 0 else 1e-10
    eq_t   = math.exp(-q * t_years)
    er_t   = math.exp(-r * t_years)
    _sqrt2pi= math.sqrt(2.0 * math.pi)

    # Guard: avoid division by zero
    safe_iv = cp.where(cp_ivs > 0, cp_ivs, 1e-8)
    safe_S  = cp.where(cp_spots > 0, cp_spots, 1e-8)
    safe_K  = cp.where(cp_strikes > 0, cp_strikes, 1e-8)

    d1 = (cp.log(safe_S / safe_K) + (r - q + 0.5 * safe_iv ** 2) * t_years) / (safe_iv * sqrt_t)
    d2 = d1 - safe_iv * sqrt_t

    _sqrt2 = math.sqrt(2.0)
    cdf_d1  = 0.5 * (1.0 + scp.erf( d1 / _sqrt2))
    cdf_nd1 = 0.5 * (1.0 + scp.erf(-d1 / _sqrt2))
    cdf_d2  = 0.5 * (1.0 + scp.erf( d2 / _sqrt2))
    cdf_nd2 = 0.5 * (1.0 + scp.erf(-d2 / _sqrt2))
    nd1 = cp.exp(-0.5 * d1 ** 2) / _sqrt2pi

    # Delta
    delta = cp.where(cp_is_call, eq_t * cdf_d1, -eq_t * cdf_nd1)

    # Gamma
    gamma = eq_t * nd1 / (safe_S * safe_iv * sqrt_t)

    # Vega
    vega = safe_S * eq_t * nd1 * sqrt_t * 0.01

    # Vanna
    vanna = -eq_t * nd1 * d2 / safe_iv * 0.01

    # Charm
    charm_num = 2.0 * (r - q) * t_years - d2 * safe_iv * sqrt_t
    charm_den = 2.0 * t_years * safe_iv * sqrt_t
    charm_call = ( q * eq_t * cdf_d1  - eq_t * nd1 * charm_num / charm_den) / 365.0
    charm_put  = (-q * eq_t * cdf_nd1 - eq_t * nd1 * charm_num / charm_den) / 365.0
    charm = cp.where(cp_is_call, charm_call, charm_put)

    # Theta
    theta_call = (
        -(safe_S * safe_iv * eq_t * nd1) / (2.0 * sqrt_t)
        - r * safe_K * er_t * cdf_d2
        + q * safe_S * eq_t * cdf_d1
    ) / 365.0
    theta_put = (
        -(safe_S * safe_iv * eq_t * nd1) / (2.0 * sqrt_t)
        + r * safe_K * er_t * cdf_nd2
        - q * safe_S * eq_t * cdf_nd1
    ) / 365.0
    theta = cp.where(cp_is_call, theta_call, theta_put)

    # Mask invalid inputs
    valid = (cp_ivs > 0) & (cp_spots > 0) & (cp_strikes > 0) & (t_years > 0)
    for arr in (delta, gamma, vega, vanna, charm, theta):
        arr[~valid] = 0.0

    agg = None
    if ois is not None and mults is not None:
        cp_ois = cp.asarray(ois.astype(np.float64))
        cp_mults = cp.asarray(mults.astype(np.float64))
        
        # Keep GEX convention aligned with L1 mainline (1% spot-move MMUSD):
        # gamma * OI * multiplier * S^2 * 0.01, then normalize to USD millions.
        gex = gamma * cp_ois * (safe_S ** 2) * cp_mults * 0.01
        gex = cp.where(valid, gex, 0.0)
        vanna_exp = cp.where(valid, vanna * cp_ois * cp_mults, 0.0)
        charm_exp = cp.where(valid, charm * cp_ois * cp_mults, 0.0)
        
        call_mask = cp_is_call
        put_mask = ~cp_is_call
        
        call_gex_arr = cp.where(call_mask, gex, cp.array(0.0, dtype=cp.float64))
        put_gex_arr = cp.where(put_mask, gex, cp.array(0.0, dtype=cp.float64))
        
        total_call_gex = float(cp.sum(call_gex_arr).item())
        total_put_gex = float(cp.sum(put_gex_arr).item())
        
        strikes_np = cp.asnumpy(cp_strikes).astype(np.float64)
        call_gex_np = cp.asnumpy(call_gex_arr).astype(np.float64)
        put_gex_np = cp.asnumpy(put_gex_arr).astype(np.float64)
        spots_np = cp.asnumpy(cp_spots).astype(np.float64)
        valid_np = cp.asnumpy(valid).astype(np.bool_)
        if valid_np.any():
            spot_ref = float(np.median(spots_np[valid_np]))
        elif spots_np.size > 0:
            spot_ref = float(spots_np[0])
        else:
            spot_ref = 0.0

        call_wall, put_wall, max_call_gex, max_put_gex = rust_select_walls(
            strikes=strikes_np,
            call_gex=call_gex_np,
            put_gex=put_gex_np,
            spot_ref=spot_ref,
        )
        call_wall = call_wall if max_call_gex > 0 else None
        put_wall = put_wall if max_put_gex > 0 else None
        
        agg = {
            "net_gex": (total_call_gex - total_put_gex) / _GEX_SCALE_MILLION,
            "total_call_gex": total_call_gex / _GEX_SCALE_MILLION,
            "total_put_gex": total_put_gex / _GEX_SCALE_MILLION,
            "max_call_gex": max_call_gex,
            "max_put_gex": max_put_gex,
            "call_wall": call_wall,
            "put_wall": put_wall,
            "net_vanna": float(cp.sum(vanna_exp).item()) / _GEX_SCALE_MILLION,
            "net_charm": float(cp.sum(charm_exp).item()) / _GEX_SCALE_MILLION,
        }

    # Transfer back to CPU — the rest of the pipeline is CPU-side
    greeks = {
        "delta":  cp.asnumpy(delta),
        "gamma":  cp.asnumpy(gamma),
        "vega":   cp.asnumpy(vega),
        "vanna":  cp.asnumpy(vanna),
        "charm":  cp.asnumpy(charm),
        "theta":  cp.asnumpy(theta),
    }
    return greeks, agg


def compute_greeks_batch(
    spots:   np.ndarray,
    strikes: np.ndarray,
    ivs:     np.ndarray,
    t_years: float,
    is_call: np.ndarray,
    r: float = 0.05,
    q: float = 0.0,
    ois:     np.ndarray | None = None,
    mults:   np.ndarray | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, float] | None]:
    """
    Batch-compute BSM Greeks for an entire option chain.

    3-tier execution priority:
      1. CuPy GPU kernel  (if cupy installed + CUDA device present)
      2. Numba JIT+prange (if numba installed)
      3. Rust BSM owner (via legacy NumPy-tier entrypoint)

    Args:
        spots    : float64 array, spot price for each contract
        strikes  : float64 array, strike price per contract
        ivs      : float64 array, implied volatility (decimal) per contract
        t_years  : scalar, trading time-to-maturity in years
        is_call  : bool array, True = Call, False = Put
        r        : risk-free rate (annual, continuous)
        q        : dividend yield (annual, continuous)

    Returns:
        dict with keys: delta, gamma, vega, vanna, charm, theta (each float64 ndarray)
    """
    # Tier 1: GPU path
    if _CUPY_AVAILABLE:
        try:
            return _bsm_batch_cupy(spots, strikes, ivs, t_years, is_call, r, q, ois, mults)
        except Exception as exc:
            logger.warning(f"[bsm_fast] CuPy GPU path failed ({exc}), falling back to Numba.")

    # CPU paths
    greeks = None
    # Tier 2: Numba JIT path
    if _NUMBA_AVAILABLE:
        d, g, ve, va, ch, th = _bsm_batch_numba(
            spots.astype(np.float64),
            strikes.astype(np.float64),
            ivs.astype(np.float64),
            float(t_years),
            is_call.astype(np.bool_),
            float(r), float(q),
        )
        greeks = {"delta": d, "gamma": g, "vega": ve, "vanna": va, "charm": ch, "theta": th}
    else:
        # Tier 3: Rust-owned BSM path
        greeks = _bsm_batch_numpy(spots, strikes, ivs, t_years, is_call, r, q)
        
    agg = None
    if ois is not None and mults is not None:
        agg = rust_aggregate_from_greeks(
            gamma=greeks["gamma"],
            vanna=greeks["vanna"],
            charm=greeks["charm"],
            spots=spots,
            strikes=strikes,
            is_call=is_call,
            ivs=ivs,
            t_years=t_years,
            ois=ois,
            mults=mults,
        )
        
    return greeks, agg


def warmup() -> None:
    """Pre-compile CuPy/Numba path with a tiny synthetic batch."""
    if not _CUPY_AVAILABLE and not _NUMBA_AVAILABLE:
        logger.info("[bsm_fast.warmup] Neither CuPy nor Numba present — no-op.")
        return

    tier = "CuPy GPU" if _CUPY_AVAILABLE else "Numba JIT"
    logger.info(f"[bsm_fast.warmup] Starting {tier} pre-compilation …")
    t0 = time.perf_counter()

    n = 20
    spots   = np.full(n, 580.0)
    strikes = np.linspace(560.0, 600.0, n)
    ivs     = np.full(n, 0.18)
    is_call = np.array([i % 2 == 0 for i in range(n)])
    t_years = 2.0 / 9.25 / 252  # ~2h remaining in session

    _ = compute_greeks_batch(spots, strikes, ivs, t_years, is_call)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    logger.info(
        f"[bsm_fast.warmup] {tier} pre-compilation complete in {elapsed_ms:.0f} ms — "
        "subsequent calls will be near-zero latency."
    )
