"""Measure how often price hits each golden-fib zone intraday vs at close."""
import numpy as np
import yfinance as yf

spy = yf.download('SPY', start='2017-12-01', end='2026-08-01', progress=False)
c = np.array([float(x) for x in spy[('Close', 'SPY')]])
h = np.array([float(x) for x in spy[('High', 'SPY')]])
l = np.array([float(x) for x in spy[('Low', 'SPY')]])
n = len(c)

# results buckets: (label, list of 5d forward returns from today's CLOSE)
buckets = {
    "deep_-1372": [],
    "zone_-1272": [],
    "bounce_0": [],
    "above_0": [],
}
counts = {k: 0 for k in buckets}

for i in range(1, n - 5):
    R = h[i - 1] - l[i - 1]
    if R <= 0 or R / c[i - 1] < 0.001:
        continue
    dn_1372 = l[i - 1] - 0.372 * R
    dn_1272 = l[i - 1] - 0.272 * R
    zero = l[i - 1]
    tl, tc = l[i], c[i]
    r5 = (c[i + 5] - tc) / tc

    if tl <= dn_1372:
        buckets["deep_-1372"].append(r5); counts["deep_1372"] += 1
    elif tl <= dn_1272:
        buckets["zone_1272"].append(r5); counts["zone_1272"] += 1
    elif tl <= zero + 0.10 * R:
        buckets["bounce_0"].append(r5); counts["bounce_0"] += 1
    else:
        buckets["above_0"].append(r5); counts["above_0"] += 1

print("=== INTRADAY LOW vs YESTERDAY'S FIB GRID (SPY 2018-2026) ===")
print(f"Total days: {n}")
print("-" * 84)
print(f"{'Today LOW reached':<44} {'days':>6} {'pct':>6} {'5d fwd from CLOSE':>18} {'hit>0':>7}")
print("-" * 84)
rows = [
    ("below -1.372  (deep buy zone)", "deep_1372"),
    ("-1.272 .. -1.372  (buy zone)", "zone_1272"),
    ("0 .. +0.1R  (bounced off 0)", "bounce_0"),
    ("above +0.1R all day (never near 0)", "above_0"),
]
for label, key in rows:
    cnt = counts[key]
    arr = buckets[key]
    m = np.mean(arr) * 100 if arr else 0.0
    hh = np.mean(np.array(arr) > 0) * 100 if arr else 0.0
    print(f"{label:<44} {cnt:>6} {cnt/n*100:>6.1f}% {m:>10.3f}% {hh:>8.1f}%")

print()
print("KEY INSIGHT: bounce_0 events are the 'needed' case the user described")
print("- 'bounce off 0' happens {:.1f}% of days with +{:.3f}% 5d fwd".format(
    counts['bounce_0']/n*100, (np.mean(buckets['bounce_0'])*100 if buckets['bounce_0'] else 0)))