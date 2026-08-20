"""Test open/close anchors for the golden fib."""
import numpy as np
import yfinance as yf

spy = yf.download('SPY', start='2017-12-01', end='2026-08-01', progress=False)
c = np.array([float(x) for x in spy[('Close','SPY')]])
h = np.array([float(x) for x in spy[('High','SPY')]])
l = np.array([float(x) for x in spy[('Low','SPY')]])
o = np.array([float(x) for x in spy[('Open','SPY')]])


def grid_oc(op, cl, k1, k2):
    """Place 0/1 lines so that: lo - k1*R = open AND hi + k2*R = close.

    i.e. the open sits ON the -k1-line and the close ON the +k2-line.
    R = range between the 0/1 lines. hi = lo + R.
    """
    d = cl - op
    R = abs(d) / (1.0 + k1 + k2)
    if R <= 1e-9:
        return op - 1.0, op + 1.0
    if d >= 0:  # up day: open is the lower side
        lo = op + k1 * R
        return lo, lo + R
    else:       # down day: close is the lower side, mirror
        lo = cl - k1 * R  # lower line below the close? careful
        # We want the SAME geometry: lower line at distance k1*R below open-side.
        # For down day, mirror: lower line = close + k2*R, upper = open - k1*R
        hi = op - k1 * R
        return hi - R, hi


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
    print(f"{label:<46} FL5d={fl[0]:+.3f}% hit={fl[1]:.1f}% n={fl[2]:>3}  |  FU5d={fu[0]:+.3f}% hit={fu[1]:.1f}% n={fu[2]:>3}")


print("=== OPEN/CLOSE ANCHOR VARIANTS (SPY 2018-2026, 5d fwd) ===")
print("FL=fade lower (buy dips, want +). FU=fade upper (want -).")
print("-" * 100)

test("BASELINE: LOW->HIGH",
     lambda i: (l[i - 1], h[i - 1]))
test("0=O,1=C (body)",
     lambda i: (min(o[i - 1], c[i - 1]), max(o[i - 1], c[i - 1])))
test("(-1.272)@O -> (+1.372)@C",
     lambda i: _g(o[i - 1], c[i - 1], 0.272, 0.372))
test("(-1.372)@O -> (+1.272)@C",
     lambda i: _g(o[i - 1], c[i - 1], 0.372, 0.272))
test("(-1.272)@O -> (+1.272)@C",
     lambda i: _g(o[i - 1], c[i - 1], 0.272, 0.272))
test("(-1.372)@O -> (+1.372)@C",
     lambda i: _g(o[i - 1], c[i - 1], 0.372, 0.372))
print()


def _g(op, cl, k1, k2):
    return grid_oc(op, cl, k1, k2)


def grid_oc(op, cl, k1, k2):
    d = cl - op
    if abs(d) < 1e-9:
        return op - 1.0, op + 1.0
    s = 1 if d >= 0 else -1
    R = abs(d) / (1.0 + k1 + k2)
    lo = min(op, cl) + (k1 * R if s > 0 else k2 * R)
    hi = lo + R
    return lo, hi