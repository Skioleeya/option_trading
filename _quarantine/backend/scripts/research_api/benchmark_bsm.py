"""
BSM Greeks 计算性能基准测试
============================
对比三种实现方式的速度：

  1. [BASELINE]  Pure Python (math模块，逐合约调用) — 现有实现
  2. [NUMPY]     NumPy 完全向量化 (整链一次调用，无Python循环)
  3. [NUMBA]     Numba JIT @njit + 并行 prange   (第一次调用含编译时间)

运行方法:
  cd e:/US.market/Option_v3/backend
  python scripts/research_api/benchmark_bsm.py

依赖:
  pip install numba        (Numba 可选，未安装时跳过该测试)
  numpy 已是系统依赖
"""

import sys
import os
import time
import math
import random
import statistics

import numpy as np

# --------------------------------------------------------------------------- #
# 可选: Numba JIT
# --------------------------------------------------------------------------- #
try:
    from numba import njit, prange  # type: ignore
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    print("[WARN] numba 未安装，Numba 测试将跳过。运行: pip install numba")


# =========================================================================== #
# Version 1: BASELINE — Pure Python (与 bsm.py 完全等价)
# =========================================================================== #

def _norm_cdf_py(x: float) -> float:
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def _norm_pdf_py(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

def compute_greeks_baseline(spot, strike, iv, t_years, is_call, r=0.05, q=0.0):
    """原始纯 Python 实现（对标 bsm.py compute_greeks）"""
    if iv <= 0 or spot <= 0 or strike <= 0 or t_years <= 0:
        return None
    sqrt_t = math.sqrt(t_years)
    d1 = (math.log(spot / strike) + (r - q + 0.5 * iv * iv) * t_years) / (iv * sqrt_t)
    d2 = d1 - iv * sqrt_t
    nd1 = _norm_pdf_py(d1)
    eq_t = math.exp(-q * t_years)
    er_t = math.exp(-r * t_years)

    if is_call:
        delta = eq_t * _norm_cdf_py(d1)
    else:
        delta = -eq_t * _norm_cdf_py(-d1)

    gamma = eq_t * nd1 / (spot * iv * sqrt_t)
    vega  = spot * eq_t * nd1 * sqrt_t * 0.01
    vanna = -eq_t * nd1 * d2 / iv
    charm_num = (2.0 * (r - q) * t_years - d2 * iv * sqrt_t)
    charm_den = (2.0 * t_years * iv * sqrt_t)
    charm = -eq_t * nd1 * charm_num / charm_den

    return {
        "delta": delta,
        "gamma": gamma,
        "vega":  vega,
        "vanna": vanna * 0.01,
        "charm": charm / 365.0,
    }

def run_baseline_chain(spots, strikes, ivs, t_years, opt_types, r=0.05, q=0.0):
    """对整链逐合约循环调用，模拟 _enrich_chain_with_local_greeks 行为"""
    results = []
    for i in range(len(spots)):
        g = compute_greeks_baseline(spots[i], strikes[i], ivs[i], t_years, opt_types[i], r, q)
        results.append(g)
    return results


# =========================================================================== #
# Version 2: NUMPY — 完全向量化（无 Python 循环）
# =========================================================================== #

def compute_greeks_numpy(
    spots: np.ndarray,
    strikes: np.ndarray,
    ivs: np.ndarray,
    t_years: float,
    is_call: np.ndarray,   # bool array
    r: float = 0.05,
    q: float = 0.0,
) -> dict:
    """NumPy 向量化 BSM — 整链一次计算，无 Python 循环"""
    sqrt_t = np.sqrt(t_years)
    inv_iv_sqrt_t = 1.0 / (ivs * sqrt_t)

    d1 = (np.log(spots / strikes) + (r - q + 0.5 * ivs * ivs) * t_years) * inv_iv_sqrt_t
    d2 = d1 - ivs * sqrt_t

    # norm_pdf 和 norm_cdf 的向量化版本
    nd1 = np.exp(-0.5 * d1 * d1) / np.sqrt(2.0 * np.pi)
    cdf_d1  = 0.5 * (1.0 + np.vectorize(math.erf)(d1  / math.sqrt(2.0)))
    cdf_nd1 = 0.5 * (1.0 + np.vectorize(math.erf)(-d1 / math.sqrt(2.0)))

    # 使用 scipy.special.ndtr 更高效 (若有 scipy)
    try:
        from scipy.special import ndtr  # type: ignore
        cdf_d1  = ndtr(d1)
        cdf_nd1 = ndtr(-d1)
        cdf_d2  = ndtr(d2)
        cdf_nd2 = ndtr(-d2)
    except ImportError:
        cdf_d2  = 0.5 * (1.0 + np.vectorize(math.erf)(d2  / math.sqrt(2.0)))
        cdf_nd2 = 0.5 * (1.0 + np.vectorize(math.erf)(-d2 / math.sqrt(2.0)))

    eq_t = math.exp(-q * t_years)
    er_t = math.exp(-r * t_years)

    # Delta (向量化条件赋值)
    delta = np.where(is_call,
                     eq_t * cdf_d1,
                    -eq_t * cdf_nd1)

    gamma = eq_t * nd1 / (spots * ivs * sqrt_t)
    vega  = spots * eq_t * nd1 * sqrt_t * 0.01
    vanna = -eq_t * nd1 * d2 / ivs * 0.01

    charm_num = 2.0 * (r - q) * t_years - d2 * ivs * sqrt_t
    charm_den = 2.0 * t_years * ivs * sqrt_t
    charm = -eq_t * nd1 * charm_num / charm_den / 365.0

    return {
        "delta": delta,
        "gamma": gamma,
        "vega":  vega,
        "vanna": vanna,
        "charm": charm,
    }


# =========================================================================== #
# Version 3: NUMBA JIT — 批量编译 + prange 并行
# =========================================================================== #

if NUMBA_AVAILABLE:
    @njit(parallel=True, fastmath=True, cache=True)
    def compute_greeks_numba(
        spots, strikes, ivs, t_years, is_call_arr,
        r=0.05, q=0.0
    ):
        """Numba JIT + prange 并行: 编译后速度接近原生 C"""
        n = len(spots)
        delta_arr = np.empty(n)
        gamma_arr = np.empty(n)
        vega_arr  = np.empty(n)
        vanna_arr = np.empty(n)
        charm_arr = np.empty(n)

        sqrt_t = math.sqrt(t_years)
        eq_t = math.exp(-q * t_years)
        er_t = math.exp(-r * t_years)
        _SQRT2PI = math.sqrt(2.0 * math.pi)
        _SQRT2   = math.sqrt(2.0)

        for i in prange(n):  # 并行循环
            S  = spots[i]
            K  = strikes[i]
            iv = ivs[i]
            if iv <= 0.0 or S <= 0.0 or K <= 0.0:
                delta_arr[i] = gamma_arr[i] = vega_arr[i] = vanna_arr[i] = charm_arr[i] = 0.0
                continue

            d1 = (math.log(S / K) + (r - q + 0.5 * iv * iv) * t_years) / (iv * sqrt_t)
            d2 = d1 - iv * sqrt_t

            # norm_pdf
            nd1 = math.exp(-0.5 * d1 * d1) / _SQRT2PI
            # norm_cdf via erf
            cdf_d1  = 0.5 * (1.0 + math.erf( d1 / _SQRT2))
            cdf_nd1 = 0.5 * (1.0 + math.erf(-d1 / _SQRT2))

            if is_call_arr[i]:
                delta_arr[i] = eq_t * cdf_d1
            else:
                delta_arr[i] = -eq_t * cdf_nd1

            gamma_arr[i] = eq_t * nd1 / (S * iv * sqrt_t)
            vega_arr[i]  = S * eq_t * nd1 * sqrt_t * 0.01
            vanna_arr[i] = -eq_t * nd1 * d2 / iv * 0.01

            charm_num = 2.0 * (r - q) * t_years - d2 * iv * sqrt_t
            charm_den = 2.0 * t_years * iv * sqrt_t
            charm_arr[i] = -eq_t * nd1 * charm_num / charm_den / 365.0

        return delta_arr, gamma_arr, vega_arr, vanna_arr, charm_arr


# =========================================================================== #
# 测试数据生成
# =========================================================================== #

def generate_option_chain(n=150, spot=580.0):
    """模拟 SPY 0DTE ATM±80 strike 的期权链（约 150 合约）"""
    random.seed(42)
    strikes  = [round(spot - 75 + i, 1) for i in range(n)]  # 连续 strike
    ivs      = [max(0.05, 0.15 + random.gauss(0, 0.03) + abs(strikes[i] - spot) * 0.001)
                for i in range(n)]
    is_calls = [i % 2 == 0 for i in range(n)]  # 交替 Call/Put
    spots    = [spot] * n
    return spots, strikes, ivs, is_calls


# =========================================================================== #
# 基准测试函数
# =========================================================================== #

def benchmark(func, *args, warmup=3, runs=50):
    """运行 warmup 次预热 + runs 次计时，返回中位数/最小/最大时间(ms)"""
    for _ in range(warmup):
        func(*args)
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        func(*args)
        times.append((time.perf_counter() - t0) * 1000.0)  # → ms
    return {
        "median_ms": round(statistics.median(times), 4),
        "min_ms":    round(min(times), 4),
        "max_ms":    round(max(times), 4),
        "mean_ms":   round(statistics.mean(times), 4),
    }


# =========================================================================== #
# Main
# =========================================================================== #

def main():
    T_YEARS = 2.5 / 9.25 / 252   # 2.5 小时剩余，约 0.00107 年

    print("=" * 65)
    print("  BSM Greeks — 计算性能基准测试 (Benchmark)")
    print("=" * 65)

    # ---- 不同链规模 ----
    for N in [60, 150, 300, 600]:
        spots_list, strikes_list, ivs_list, is_calls_list = generate_option_chain(N)
        spots_np    = np.array(spots_list,   dtype=np.float64)
        strikes_np  = np.array(strikes_list, dtype=np.float64)
        ivs_np      = np.array(ivs_list,     dtype=np.float64)
        is_call_np  = np.array(is_calls_list, dtype=np.bool_)

        print(f"\n{'─'*65}")
        print(f"  链规模: {N} 个合约 (模拟 ATM±{N//2} Strike，SPY 0DTE)")
        print(f"{'─'*65}")

        # --- Baseline ---
        b_res = benchmark(
            run_baseline_chain,
            spots_list, strikes_list, ivs_list, T_YEARS, is_calls_list,
        )
        print(f"  [BASELINE Python]  中位={b_res['median_ms']:.4f} ms  "
              f"最小={b_res['min_ms']:.4f} ms  最大={b_res['max_ms']:.4f} ms")

        # --- NumPy ---
        n_res = benchmark(
            compute_greeks_numpy,
            spots_np, strikes_np, ivs_np, T_YEARS, is_call_np,
        )
        speedup_np = b_res["median_ms"] / n_res["median_ms"]
        print(f"  [NUMPY  Vector]    中位={n_res['median_ms']:.4f} ms  "
              f"最小={n_res['min_ms']:.4f} ms  最大={n_res['max_ms']:.4f} ms  "
              f"→ \033[92m{speedup_np:.1f}× 加速\033[0m")

        # --- Numba ---
        if NUMBA_AVAILABLE:
            # 首次调用含编译开销，单独计时
            t_compile = time.perf_counter()
            compute_greeks_numba(spots_np, strikes_np, ivs_np, T_YEARS, is_call_np)
            compile_ms = (time.perf_counter() - t_compile) * 1000.0

            nb_res = benchmark(
                compute_greeks_numba,
                spots_np, strikes_np, ivs_np, T_YEARS, is_call_np,
            )
            speedup_nb = b_res["median_ms"] / nb_res["median_ms"]
            print(f"  [NUMBA  JIT+par]   中位={nb_res['median_ms']:.4f} ms  "
                  f"最小={nb_res['min_ms']:.4f} ms  最大={nb_res['max_ms']:.4f} ms  "
                  f"→ \033[96m{speedup_nb:.1f}× 加速\033[0m  "
                  f"(首次编译: {compile_ms:.0f} ms)")
        else:
            print("  [NUMBA  JIT+par]   ⚠ 未安装，跳过 (pip install numba)")

    print(f"\n{'═'*65}")
    print("  ✅ 测试完毕")
    print(f"{'═'*65}")
    print()
    print("  结论:")
    print("  - NumPy 向量化可立即应用到 bsm.py，无需任何新依赖")
    print("  - Numba JIT 首次调用有编译延迟(一次性)，后续速度最快")
    print("  - 推荐路径: 先部署 NumPy 版本，再追加 Numba 作为可选快速路径")


if __name__ == "__main__":
    main()
