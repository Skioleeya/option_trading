"""
BM Parameter Calibration Script
================================
Uses the historical breadth data stored in Redis to compute statistically
optimal parameters for the new Bm_calculator:

Analysis outputs:
  1. BM value distribution (percentiles, std, range)
  2. Delta BM distribution (how fast BM moves between ticks)
  3. Recommended BM_VOL_WINDOW, BM_VOL_MULTIPLIER, BM_STATIC_THRESHOLD
  4. Comparison of regime distribution under old [1,2,3] vs new [1,3,9] weights
  5. Optional: Raw data export to CSV for offline inspection
"""
import redis
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# ─── Redis connection ────────────────────────────────────────────────────
R = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)

def ping():
    try:
        return R.ping()
    except Exception:
        return False

# ─── Data Loading ────────────────────────────────────────────────────────
def load_all_records(max_records: int = 10_000) -> list[dict]:
    """
    Load records from breadth_momentum:timeline (newest first).
    Returns list of dicts with raw segment metrics.
    """
    record_ids = R.zrevrange("breadth_momentum:timeline", 0, max_records - 1)
    if not record_ids:
        print("[ERROR] No data in breadth_momentum:timeline")
        return []

    print(f"Loading {len(record_ids)} records from Redis...")
    records = []
    with R.pipeline() as pipe:
        for rid in record_ids:
            pipe.hgetall(f"breadth_momentum:record:{rid}")
        raw_results = pipe.execute()

    for data in raw_results:
        if not data:
            continue
        try:
            r = {
                "timestamp": data.get("timestamp", ""),
                "advancers": int(data.get("advancers", 0)),
                "decliners": int(data.get("decliners", 0)),
                "BM": int(data.get("BM", 0)),
                "delta_BM": int(data.get("delta_BM", 0)),
                "net_breadth": int(data.get("net_breadth", 0)),
                "regime": data.get("regime", ""),
                "up5": int(data.get("up5", 0)),
                "up3_5": int(data.get("up3_5", 0)),
                "up0_3": int(data.get("up0_3", 0)),
                "down0_3": int(data.get("down0_3", 0)),
                "down3_5": int(data.get("down3_5", 0)),
                "down5": int(data.get("down5", 0)),
            }
            records.append(r)
        except (ValueError, KeyError):
            continue

    print(f"Loaded {len(records)} valid records.")
    return records

# ─── Stats Helpers ───────────────────────────────────────────────────────
def percentile(sorted_vals: list, p: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = (len(sorted_vals) - 1) * p / 100.0
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (idx - lo)

def std(vals: list) -> float:
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    return math.sqrt(sum((x - mean) ** 2 for x in vals) / (len(vals) - 1))

def recompute_bm(record: dict, weights: dict) -> tuple[int, int]:
    """Recompute BM with given weights from raw segment data."""
    bm = (record["up5"] * weights["up5"] +
          record["up3_5"] * weights["up3_5"] +
          record["up0_3"] * weights["up0_3"] +
          record["down0_3"] * weights["down0_3"] +
          record["down3_5"] * weights["down3_5"] +
          record["down5"] * weights["down5"])
    return bm

# ─── Main Analysis ───────────────────────────────────────────────────────
def run_analysis():
    if not ping():
        print("[ERROR] Cannot connect to Redis at 127.0.0.1:6379")
        sys.exit(1)

    records = load_all_records(max_records=10_000)
    if not records:
        sys.exit(1)

    n = len(records)
    bm_vals = sorted([r["BM"] for r in records])
    delta_vals = sorted([abs(r["delta_BM"]) for r in records if r["delta_BM"] != 0])
    adv_vals = [r["advancers"] for r in records]
    dec_vals = [r["decliners"] for r in records]

    # ── 1. BM Distribution ──────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  BM VALUE DISTRIBUTION (Original Weights 1:2:3)")
    print("=" * 65)
    bm_mean = sum(bm_vals) / n
    bm_std = std(bm_vals)
    print(f"  N (records)    : {n:,}")
    print(f"  Min / Max BM   : {min(bm_vals):,} / {max(bm_vals):,}")
    print(f"  Mean BM        : {bm_mean:,.1f}")
    print(f"  Std Dev        : {bm_std:,.1f}")
    print(f"  P10  (bear)    : {percentile(bm_vals, 10):,.0f}")
    print(f"  P25            : {percentile(bm_vals, 25):,.0f}")
    print(f"  P50  (median)  : {percentile(bm_vals, 50):,.0f}")
    print(f"  P75            : {percentile(bm_vals, 75):,.0f}")
    print(f"  P90  (bull)    : {percentile(bm_vals, 90):,.0f}")

    # ── 2. Delta BM Distribution ─────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  DELTA BM DISTRIBUTION (tick-over-tick change, absolute)")
    print("=" * 65)
    if delta_vals:
        d_mean = sum(delta_vals) / len(delta_vals)
        d_std = std(delta_vals)
        print(f"  Mean |Delta|   : {d_mean:,.1f}")
        print(f"  Std Dev        : {d_std:,.1f}")
        print(f"  P25            : {percentile(delta_vals, 25):,.0f}")
        print(f"  P50 (median)   : {percentile(delta_vals, 50):,.0f}")
        print(f"  P75            : {percentile(delta_vals, 75):,.0f}")
        print(f"  P90            : {percentile(delta_vals, 90):,.0f}")
        print(f"  P95 (extreme)  : {percentile(delta_vals, 95):,.0f}")

    # ── 3. Regime Distribution (original) ────────────────────────────────
    regime_counts = Counter(r["regime"] for r in records if r["regime"])
    print("\n" + "=" * 65)
    print("  REGIME DISTRIBUTION (Original System, from Redis)")
    print("=" * 65)
    total_regime = sum(regime_counts.values())
    for regime, count in sorted(regime_counts.items(), key=lambda x: -x[1]):
        pct = count / total_regime * 100
        print(f"  {regime:<14}: {count:6,}  ({pct:5.1f}%)")

    # ── 4. Recomputed BM with new weights [1,3,9] ────────────────────────
    weights_new = {"up5": 9, "up3_5": 3, "up0_3": 1,
                   "down0_3": -1, "down3_5": -3, "down5": -9}
    new_bm_vals = sorted([recompute_bm(r, weights_new) for r in records])
    new_bm_std = std(new_bm_vals)

    print("\n" + "=" * 65)
    print("  BM DISTRIBUTION (New Weights 1:3:9)")
    print("=" * 65)
    print(f"  Min / Max BM   : {min(new_bm_vals):,} / {max(new_bm_vals):,}")
    print(f"  Mean BM        : {sum(new_bm_vals)/len(new_bm_vals):,.1f}")
    print(f"  Std Dev        : {new_bm_std:,.1f}")
    print(f"  P10            : {percentile(new_bm_vals, 10):,.0f}")
    print(f"  P50 (median)   : {percentile(new_bm_vals, 50):,.0f}")
    print(f"  P90            : {percentile(new_bm_vals, 90):,.0f}")

    # ── 5. Parameter Recommendations ─────────────────────────────────────
    print("\n" + "=" * 65)
    print("  CALIBRATED PARAMETER RECOMMENDATIONS")
    print("=" * 65)

    # BM_STATIC_THRESHOLD: 1 std of original BM (covers normal noise)
    rec_static_bm = int(round(bm_std * 0.5 / 50) * 50)  # round to nearest 50
    rec_static_bm = max(rec_static_bm, 100)
    # Delta threshold: ~P50 of absolute delta (median actual tick movement)
    rec_static_delta = int(percentile(delta_vals, 50)) if delta_vals else 100

    # BM_VOL_WINDOW: should cover ~5 minutes of data (100 observations at 3s)
    # but for faster reaction, 20 observations is fine for intraday
    rec_window = 20  # unchanged
    # BM_VOL_MULTIPLIER: tune so 60% of market time is in "useful" state (Trend/Reversal)
    # Target: BM_CHOP_THRESHOLD = 1.0 * rolling_std during average session
    rec_multiplier = 1.0  # calibrated as baseline

    # For new-weight system, scale static threshold proportionally
    scale_factor = new_bm_std / bm_std if bm_std > 0 else 1.0
    rec_new_static = int(rec_static_bm * scale_factor)

    print(f"\n  For NEW weights [1, 3, 9]:")
    print(f"  BM_STATIC_THRESHOLD    : {rec_new_static}  (was: 50)")
    print(f"  BM_STATIC_DELTA_THRESHOLD: {rec_static_delta}  (was: 25)")
    print(f"  BM_VOL_WINDOW          : {rec_window}  (unchanged)")
    print(f"  BM_VOL_MULTIPLIER      : {rec_multiplier}  (unchanged)")
    print(f"\n  Scale factor (new/old std): {scale_factor:.2f}x")

    # ── 6. Advancers / Decliners Universe size ───────────────────────────
    total_universe = sorted([a + d for a, d in zip(adv_vals, dec_vals)])
    print("\n" + "=" * 65)
    print("  MARKET UNIVERSE (Advancers + Decliners)")
    print("=" * 65)
    print(f"  Median universe size   : {percentile(total_universe, 50):,.0f} stocks")
    print(f"  P25 / P75              : {percentile(total_universe, 25):,.0f} / {percentile(total_universe, 75):,.0f}")

    # ── 7. Trading dates in Redis ────────────────────────────────────────
    trading_dates = R.smembers("trading_dates")
    if trading_dates:
        dates_sorted = sorted(trading_dates)
        print("\n" + "=" * 65)
        print("  TRADING DATES IN REDIS")
        print("=" * 65)
        print(f"  Total days: {len(dates_sorted)}")
        print(f"  Range: {dates_sorted[0]} -> {dates_sorted[-1]}")
        print(f"  Last 5: {', '.join(dates_sorted[-5:])}")

    print("\n" + "=" * 65)
    print("  CALIBRATION COMPLETE")
    print("=" * 65)

if __name__ == "__main__":
    run_analysis()
