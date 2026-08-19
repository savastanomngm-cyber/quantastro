"""Backtest the full pruned rulebook over historical data with 3d/5d forward.

Strategy: when rulebook says LONG (price at -1.372 fib extreme), buy and
hold for 3-5d.  When SHORT (+1.372), stay long (market drifts up).
When risk-off (size < 0.5), go flat.

The rulebook doesn't predict daily returns — it allocates based on
astro + fib confluence, and the edge compounds over multi-day holds.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from .risklayer import rulebook_output


def backtest_rulebook(
    ticker: str = "SPY",
    asset_key: str = "ES",
    start: str = "2018-01-01",
    end: str = "2026-08-01",
) -> Dict[str, Any]:
    import yfinance as yf

    data = yf.download(ticker, start=start, end=end, progress=False)
    if data.empty:
        return {"error": "no data"}

    close = np.array([float(x) for x in data[("Close", ticker)]])
    high  = np.array([float(x) for x in data[("High", ticker)]])
    low   = np.array([float(x) for x in data[("Low", ticker)]])
    open_ = np.array([float(x) for x in data[("Open", ticker)]])
    dates = data.index

    rows = []
    for i in range(1, len(data)):
        dt = dates[i]
        date_str = dt.strftime("%Y-%m-%d")
        rb = rulebook_output(
            date_str=date_str, asset=asset_key,
            prev_open=float(open_[i-1]), prev_high=float(high[i-1]),
            prev_low=float(low[i-1]), prev_close=float(close[i-1]),
            current_close=float(close[i]),
        )
        rb["close"] = float(close[i])
        rb["log_return"] = float(np.log(close[i] / close[i-1]))
        for fd in [3, 5]:
            if i + fd < len(close):
                rb[f"fwd_{fd}d"] = float(np.log(close[i + fd] / close[i]))
        rows.append(rb)

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])

    # Strategy: 3d forward returns, sized by rulebook
    strategy = np.zeros(len(df))
    for idx in range(len(df)):
        row = df.iloc[idx]
        d = row["direction"]
        sz = row.get("size_multiplier", 1.0)
        fwd = row.get("fwd_3d")
        if pd.isna(fwd):
            continue
        if sz < 0.5:
            strategy[idx] = 0.0
        elif d == "LONG":
            strategy[idx] = fwd * min(sz * 0.33, 0.50)
        elif d == "SHORT":
            strategy[idx] = fwd * 0.25  # stay long at upper extreme
        else:
            strategy[idx] = fwd * 0.15

    daily = strategy / 3.0
    df["strategy_daily"] = daily

    ann = 252
    sr = float(daily.mean() * ann)
    sv = float(daily.std() * np.sqrt(ann))
    sharpe = sr / sv if sv > 0 else 0
    bh_ret = df["log_return"]
    bh_sharpe = float(bh_ret.mean() * ann) / float(bh_ret.std() * np.sqrt(ann))

    eq = (1 + pd.Series(daily)).cumprod().values
    peak = np.maximum.accumulate(eq)
    max_dd = float(np.min((eq - peak) / peak))
    win_rate = float((daily > 0).mean())

    split = "2022-01-01"
    def pstats(mask):
        r = daily[mask]
        if len(r) == 0: return {}
        a = float(r.mean() * ann)
        v = float(r.std() * np.sqrt(ann))
        return {"n": int(mask.sum()), "sharpe": round(a/v,3) if v else 0,
                "ret": round(a,4), "dd": round(float(np.min(((1+pd.Series(r)).cumprod().values / np.maximum.accumulate((1+pd.Series(r)).cumprod().values) - 1))),4),
                "wr": round(float((r>0).mean()),3)}
    is_m = pstats(df["date"] < split)
    oos_m = pstats(df["date"] >= split)
    all_m = pstats(np.ones(len(daily), dtype=bool))

    # Fib extreme only
    fib = {}
    for ext in ["-1.372", "+1.372"]:
        s = df[df["fib_extreme"] == ext]
        f3 = s["fwd_3d"].dropna()
        f5 = s["fwd_5d"].dropna()
        fib[ext] = {"n": len(s), "m3": round(float(f3.mean()),6) if len(f3) else 0,
                    "h3": round(float((f3>0).mean()),3) if len(f3) else 0,
                    "m5": round(float(f5.mean()),6) if len(f5) else 0,
                    "h5": round(float((f5>0).mean()),3) if len(f5) else 0}

    lines = [
        f"## Rulebook Backtest (3d forward): {ticker}",
        f"**{start} → {end}** | Split: {split}",
        f"**Strategy:** LONG at -1.372 (buy dip 3d); SHORT at +1.372 (stay long); risk-off=flat",
        "",
        f"| Metric | IS | OOS | ALL | B&H |",
        f"|--------|-----|-----|-----|-----|",
        f"| Days | {is_m.get('n','-')} | {oos_m.get('n','-')} | {all_m.get('n','-')} | {len(df)} |",
        f"| Sharpe | {is_m.get('sharpe','-')} | {oos_m.get('sharpe','-')} | {all_m.get('sharpe','-')} | {bh_sharpe:.3f} |",
        f"| Ann. Ret | {is_m.get('ret',0):.2%} | {oos_m.get('ret',0):.2%} | {all_m.get('ret',0):.2%} | {float(bh_ret.mean()*ann):.2%} |",
        f"| Max DD | {is_m.get('dd',0):.2%} | {oos_m.get('dd',0):.2%} | {all_m.get('dd',0):.2%} | — |",
        f"| Win Rate | {is_m.get('wr',0):.1%} | {oos_m.get('wr',0):.1%} | {all_m.get('wr',0):.1%} | — |",
        "",
        "### Fib Extreme → Forward",
        "| Extreme | n | 3d mean | 3d hit | 5d mean | 5d hit |",
        "|---------|---|---------|--------|---------|--------|",
    ]
    for ext in ["-1.372", "+1.372"]:
        f = fib[ext]
        lines.append(f"| {ext} | {f['n']} | {f['m3']:+.4%} | {f['h3']:.1%} | {f['m5']:+.4%} | {f['h5']:.1%} |")
    lines.append("")

    return {"summary": "\n".join(lines), "sharpe": sharpe, "fib_only": fib, "df": df}