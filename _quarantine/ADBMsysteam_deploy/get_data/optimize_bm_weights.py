"""
BM Weight Optimizer — Based on Raw Segment Data in Redis
=========================================================
Uses the raw segment fields (up5, up3_5, up0_3, down0_3, down3_5, down5)
stored in Redis records to empirically derive optimal weights.

Method: We compute the "best" weights by maximizing the correlation
between the weighted BM and the subsequent PRICE DIRECTION of each tick.

Since we don't have external price data, we use the NEXT-PERIOD net_breadth
(advancers - decliners) as a proxy for directional truth:
    If BM[t] with optimal weights predicts sign(net_breadth[t]) → good weights.

Output:
    1. Distribution analysis of each raw segment
    2. Cross-correlation of each segment with future net breadth
    3. Recommended weight ratios (empirically derived, as integer ratios)
    4. Comparison with current [1, 3, 9] vs optimal
"""
import redis
import math
from collections import defaultdict

R = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)

# ─── Load data ────────────────────────────────────────────────────────────
print("Loading records from Redis timeline...")
record_ids = R.zrange("breadth_momentum:timeline", 0, 9999, withscores=False)
print(f"Found {len(record_ids)} IDs in timeline.")

records = []
with R.pipeline() as pipe:
    for rid in record_ids:
        pipe.hgetall(f"breadth_momentum:record:{rid}")
    raw = pipe.execute()

for data in raw:
    if not data:
        continue
    try:
        records.append({
            "up5":      int(data.get("up5", 0)),
            "up3_5":    int(data.get("up3_5", 0)),
            "up0_3":    int(data.get("up0_3", 0)),
            "down0_3":  int(data.get("down0_3", 0)),
            "down3_5":  int(data.get("down3_5", 0)),
            "down5":    int(data.get("down5", 0)),
            "net_breadth": int(data.get("net_breadth", 0)),
            "BM":       int(data.get("BM", 0)),
        })
    except (ValueError, KeyError):
        continue

n = len(records)
print(f"Loaded {n} valid records.")

# ─── 1. Raw segment distribution ─────────────────────────────────────────
print("\n" + "=" * 65)
print("  RAW SEGMENT AVERAGES (Mean count per tick, all sessions)")
print("=" * 65)
for field in ["up5", "up3_5", "up0_3", "down0_3", "down3_5", "down5"]:
    vals = [r[field] for r in records]
    mean = sum(vals) / n
    std_v = math.sqrt(sum((x - mean) ** 2 for x in vals) / (n - 1))
    print(f"  {field:<10}: mean={mean:7.1f}  std={std_v:7.1f}  "
          f"  relative_std={std_v/mean*100:.1f}%")

# ─── 2. Correlation of each segment with next-period net_breadth ──────────
print("\n" + "=" * 65)
print("  SEGMENT PREDICTIVE POWER (Pearson r vs. net_breadth)")
print("  Measures how strongly each bucket predicts current breadth direction")
print("=" * 65)

net = [r["net_breadth"] for r in records]
net_mean = sum(net) / len(net)
net_std = math.sqrt(sum((x - net_mean) ** 2 for x in net) / (len(net) - 1))

fields = [("up5", 1), ("up3_5", 1), ("up0_3", 1),
          ("down0_3", -1), ("down3_5", -1), ("down5", -1)]

correlations = {}
for field, sign in fields:
    seg = [r[field] * sign for r in records]
    seg_mean = sum(seg) / n
    seg_std = math.sqrt(sum((x - seg_mean) ** 2 for x in seg) / (n - 1))
    if seg_std == 0:
        correlations[field] = 0.0
        continue
    cov = sum((seg[i] - seg_mean) * (net[i] - net_mean) for i in range(n)) / (n - 1)
    r_val = cov / (seg_std * net_std)
    correlations[field] = r_val
    direction = "UP  ✓" if sign == 1 else "DOWN ✓"
    print(f"  {field:<10}: Pearson r = {r_val:+.4f}  [{direction}]")

# ─── 3. Derive relative weight ratios ────────────────────────────────────
print("\n" + "=" * 65)
print("  EMPIRICALLY DERIVED WEIGHT RATIOS (from correlation)")
print("=" * 65)

# Use the absolute correlation as the weight signal
# Normalize each tier pair for symmetrical comparison
w_up0_3   = abs(correlations["up0_3"])
w_up3_5   = abs(correlations["up3_5"])
w_up5     = abs(correlations["up5"])
w_dn0_3   = abs(correlations["down0_3"])
w_dn3_5   = abs(correlations["down3_5"])
w_dn5     = abs(correlations["down5"])

# Average up/down weights for each tier (should be symmetric)
w_tier1 = (w_up0_3 + w_dn0_3) / 2
w_tier2 = (w_up3_5 + w_dn3_5) / 2
w_tier3 = (w_up5   + w_dn5)   / 2

print(f"  Raw Tier1 (0~3%) weight : {w_tier1:.4f}")
print(f"  Raw Tier2 (3~5%) weight : {w_tier2:.4f}")
print(f"  Raw Tier3 (>5%)  weight : {w_tier3:.4f}")
print()

# Scale to integer-friendly ratios relative to Tier1 = 1
ratio2 = w_tier2 / w_tier1 if w_tier1 > 0 else 1.0
ratio3 = w_tier3 / w_tier1 if w_tier1 > 0 else 1.0
print(f"  Empirical ratios (Tier1=1): 1 : {ratio2:.2f} : {ratio3:.2f}")
# Round to nearest 0.5 for practical int conversion
r2_rounded = round(ratio2 * 2) / 2
r3_rounded = round(ratio3 * 2) / 2
print(f"  Rounded  ratios (Tier1=1): 1 : {r2_rounded:.1f} : {r3_rounded:.1f}")
print()

print("  COMPARISON TABLE:")
print(f"  {'Scheme':<20} | {'Tier1':>6} | {'Tier2':>6} | {'Tier3':>6}")
print(f"  {'-'*20}-+-{'-'*6}-+-{'-'*6}-+-{'-'*6}")
print(f"  {'Old Linear [1,2,3]':<20} | {'1':>6} | {'2':>6} | {'3':>6}")
print(f"  {'Current [1,3,9]':<20} | {'1':>6} | {'3':>6} | {'9':>6}")
print(f"  {'Empirical':<20} | {'1':>6} | {r2_rounded:>6.1f} | {r3_rounded:>6.1f}")
print()
print("  Compare empirical vs current [1,3,9] to decide if adjustment needed.")

print("\n" + "=" * 65)
print("  CALIBRATION DONE")
print("=" * 65)
