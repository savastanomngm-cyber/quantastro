"""Test: pin +1.372 line to one body edge and -1.372 to the other.

Geometry: envelope has 0-line = lo, 1-line = hi, R = hi-lo.
Extensions: +1.372-line = hi + 0.372*R,  -1.372-line = lo - 0.372*R.
We REQUIRE:
    -1.372-line = min(open, close)     (body bottom on the -1.372 line)
    +1.372-line = max(open, close)     (body top on the +1.372 line)
=>  lo - 0.372R = bottom,  hi + 0.372R = top,  hi - lo = R
=>  R = (top - bottom)/1.744
"""
import numpy as np
import yfinance as yf

spy = yf.download('SPY', start='2017-12-01', end='2026-08-01', progress=False)
c = np.array([float(x) for x in spy[('Close','SPY')]])
h = np.array([float(x) for x in spy[('High','SPY')]])
l = np.array([float(x) for x in spy[('Low','SPY')]])
o = np.array([float(x) for x in spy[('Open','SPY')]])


def anchor_oc_1372(i):
    """Envelope from yesterday's body pinned at +/-1.372 lines."""
    top = max(o[i-1], c[i-1])
    bot = min(o[i-1], c[i-1])
    body = top - bot
    R = body / 1.744
    if R <= 1e-9:
        return (top - 1, top + 1)
    hi = top - 0.372 * R
    lo = hi - R
    return lo, hi


def test(label, anchor_fn):
    fl5, fu5, fl_hit, fu_hit = [], [], [], []
    for i in range(1, len(c)):
        if i + 6 >= len(c):
            continue
        try:
            a_lo, a_hi = anchor_fn(i)
        except Exception:
            continue
        R = a_hi - a_lo
        if R <= 0 or R / c[i-1] < 0.001:
            continue
        up = a_hi + 0.272 * R
        dn = a_lo - 0.272 * R
        tc = c[i]
        if tc > up:
            r5 = (c[i + 5] - tc) / tc
            fu5.append(r5); fu_hit.append(r5 > 0)
        elif tc < dn:
            r5 = (c[i + 5] - tc) / tc
            fl5.append(r5); fl_hit.append(r5 > 0)
    fl = (np.mean(fl5) * 100 if fl5 else 0, np.mean(fl_hit) * 100 if fl_hit else 0, len(fl5))
    fu = (np.mean(fu5) * 100 if fu5 else 0, np.mean(fu_hit) * 100 if fu_hit else 0, len(fu5))
    print(f"{label:<46} FL5d={fl[0]:+.3f}% hit={fl[1]:.1f}% n={fl[2]:>4}  |  FU5d={fu[0]:+.3f}% hit={fu[1]:.1f}% n={fu[2]:>4}")


print("=== ±1.372 PINNED TO BODY EDGES ===")
print("-" * 100)
test("BASELINE: LOW->HIGH (0=L,1=H)",
     lambda i: (l[i - 1], h[i - 1]))
print(">>> NEW: -1.372@body-bottom, +1.372@body-top (0/1 inferred)")
test("(-1.372)@O, (+1.372)@C (body btw lines)",
      anchor_oc_1372)
print()

# Also test the same geometry but with extensions at +/- 1.0 (natural lines)
def anchor_oc_1(i):
    top = max(o[i-1], c[i-1])
    bot = min(o[i-1], c[i-1])
    body = top - bot
    # +1.0 pinned to top? Actually the user asked 1.372; keep variants quick.
    R = body / (2.0)  # if 0/1 are pinned to body edges
    if R <= 1e-9:
        return top - 1, top + 1
    return bot, top

test("CHECK: 0=body-low, 1=body-high (extend full body)",
      anchor_oc_lo)