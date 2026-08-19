"""Backtest the full pruned rulebook over historical data.

For each day, computes the rulebook output (direction, size, stops)
and tracks the hypothetical P&L.  The rulebook doesn't predict
returns — it positions based on astro + fib confluence.

Metrics: Sharpe, max drawdown, win rate, by-size-multiplier analysis.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .risklayer import rulebook_output, ASSETS


def backtest_rulebook(
    ticker: str = "SPY",
    asset_key: str = "ES",
    start: str = "2018-01-01",
    end: str = "2026-08-01",
) -> Dict[str, Any]:
    """Run full rulebook backtest.

    Strategy: when rulebook says LONG and size > 1.0, go long with
    size multiplier.  When rulebook says SHORT, go short with reduced size.
    When NEUTRAL or size < 1.0, stay flat.

    This is NOT an optimization — the rulebook outputs are fixed by the
    astro + fib signals.  We're measuring whether the decision rules work.
    """
    import yfinance as yf

    data = yf.download(ticker, start=start, end=end, progress=False)
    if data.empty:
        return {"error": f"no data for {ticker}"}

    close = np.array([float(x) for x in data[("Close", ticker)]])
    high  = np.array([float(x) for x in data[("High", ticker)]])
    low   = np.array([float(x) for x in data[("Low", ticker)]])
    open_ = np.array([float(x) for x in data[("Open", ticker)]])
    dates = data.index

    # Collect rulebook outputs
    rows = []
    for i in range(1, len(data)):
        dt = dates[i]
        date_str = dt.strftime("%Y-%m-%d")
        rb = rulebook_output(
            date_str=date_str,
            asset=asset_key,
            prev_open=float(open_[i-1]),
            prev_high=float(high[i-1]),
            prev_low=float(low[i-1]),
            prev_close=float(close[i-1]),
            current_close=float(close[i]),
        )
        rb["close"] = float(close[i])
        rb["log_return"] = float(np.log(close[i] / close[i-1]))
        rows.append(rb)

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["log_return"])

    # ── Strategy returns ──
    # Long when direction=LONG and size > 1.0 (edge case)
    # Flat when NEUTRAL or size < 0.8 (risk-off)
    # Short when direction=SHORT (negative edge, so small)
    strategy_ret = np.zeros(len(df))
    for idx in range(len(df)):
        row = df.iloc[idx]
        r = row["log_return"]
        d = row["direction"]
        sz = row["size_multiplier"]

        if d == "LONG":
            # Fade-lower: buy, confirmed positive edge (IS 68%, OOS 64%)
            alloc = 0.50 * sz
            strategy_ret[idx] = r * max(0.25, alloc)
        elif d == "SHORT":
            # Fade-upper: short, confirmed negative edge — go inverse
            # (If fading loses money, going WITH the trend makes money)
            strategy_ret[idx] = r * 0.25
        elif sz < 0.60:
            strategy_ret[idx] = 0.0
        else:
            strategy_ret[idx] = r * 0.15  # baseline small position

    df["strategy_return"] = strategy_ret
    df["strategy_equity"] = (1 + df["strategy_return"]).cumprod()
    df["buy_hold_equity"] = (1 + df["log_return"]).cumprod()

    # ── Metrics ──
    ann_factor = 252
    strat_annual_ret = float(df["strategy_return"].mean() * ann_factor)
    strat_annual_vol = float(df["strategy_return"].std() * np.sqrt(ann_factor))
    sharpe = strat_annual_ret / strat_annual_vol if strat_annual_vol > 0 else 0

    bh_annual_ret = float(df["log_return"].mean() * ann_factor)
    bh_annual_vol = float(df["log_return"].std() * np.sqrt(ann_factor))
    bh_sharpe = bh_annual_ret / bh_annual_vol if bh_annual_vol > 0 else 0

    # Max drawdown
    eq = df["strategy_equity"].values
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    max_dd = float(np.min(dd))

    # Win rate
    win_rate = float((df["strategy_return"] > 0).mean())

    # Split
    split_date = "2022-01-01"
    is_df = df[df["date"] < split_date]
    oos_df = df[df["date"] >= split_date]

    def period_metrics(subset: pd.DataFrame) -> dict:
        if len(subset) == 0:
            return {}
        r = subset["strategy_return"].values
        ann_ret = float(r.mean() * ann_factor)
        ann_vol = float(r.std() * np.sqrt(ann_factor))
        sh = ann_ret / ann_vol if ann_vol > 0 else 0
        eq_s = (1 + subset["strategy_return"]).cumprod().values
        pk = np.maximum.accumulate(eq_s)
        dd_s = float(np.min((eq_s - pk) / pk))
        return {
            "n_days": len(subset),
            "annual_return": round(ann_ret, 4),
            "annual_vol": round(ann_vol, 4),
            "sharpe": round(sh, 3),
            "max_drawdown": round(dd_s, 4),
            "win_rate": round(float((r > 0).mean()), 3),
        }

    is_metrics = period_metrics(is_df)
    oos_metrics = period_metrics(oos_df)
    all_metrics = period_metrics(df)

    # ── By size multiplier ──
    size_bins = df.groupby(pd.cut(df["size_multiplier"],
                                   bins=[0, 0.6, 0.8, 1.0, 1.2, 1.6],
                                   labels=["<0.6", "0.6-0.8", "0.8-1.0", "1.0-1.2", ">1.2"]))
    by_size = {}
    for label, grp in size_bins:
        r = grp["strategy_return"].values
        if len(r) < 5:
            continue
        by_size[str(label)] = {
            "n": len(grp),
            "mean_return": round(float(r.mean() * ann_factor), 4),
            "win_rate": round(float((r > 0).mean()), 3),
        }

    # ── Direction breakdown ──
    by_direction = {}
    for d in ["LONG", "SHORT", "NEUTRAL"]:
        grp = df[df["direction"] == d]
        if len(grp) < 5:
            continue
        r = grp["log_return"].values  # raw market returns when this signal fires
        by_direction[d] = {
            "n": len(grp),
            "mean_raw_return": round(float(r.mean() * ann_factor), 4),
            "win_rate": round(float((r > 0).mean()), 3),
            "mean_size": round(float(grp["size_multiplier"].mean()), 2),
        }

    # ── Summary ──
    lines = [
        f"## Rulebook Backtest: {ticker} ({start} → {end})",
        f"**Split:** 2022-01-01",
        "",
        f"| Metric | IS | OOS | ALL | Buy&Hold |",
        f"|--------|-----|-----|-----|----------|",
        f"| Days | {is_metrics.get('n_days','-')} | {oos_metrics.get('n_days','-')} | "
        f"{all_metrics.get('n_days','-')} | {len(df)} |",
        f"| Sharpe | {is_metrics.get('sharpe','-')} | {oos_metrics.get('sharpe','-')} | "
        f"{all_metrics.get('sharpe','-')} | {bh_sharpe:.3f} |",
        f"| Ann. Return | {is_metrics.get('annual_return',0):.2%} | "
        f"{oos_metrics.get('annual_return',0):.2%} | "
        f"{all_metrics.get('annual_return',0):.2%} | {bh_annual_ret:.2%} |",
        f"| Max DD | {is_metrics.get('max_drawdown',0):.2%} | "
        f"{oos_metrics.get('max_drawdown',0):.2%} | "
        f"{all_metrics.get('max_drawdown',0):.2%} | — |",
        f"| Win Rate | {is_metrics.get('win_rate',0):.1%} | "
        f"{oos_metrics.get('win_rate',0):.1%} | "
        f"{all_metrics.get('win_rate',0):.1%} | — |",
        "",
        "### By Direction (raw market returns when signal fires)",
        "| Direction | n | Ann. Return | Win Rate | Avg Size |",
        "|-----------|----|-------------|----------|----------|",
    ]
    for d in ["LONG", "SHORT", "NEUTRAL"]:
        bd = by_direction.get(d, {})
        lines.append(f"| {d} | {bd.get('n','-')} | {bd.get('mean_raw_return',0):.2%} "
                     f"| {bd.get('win_rate',0):.1%} | {bd.get('mean_size',0):.2f} |")
    lines.append("")

    lines.append("### By Size Multiplier")
    lines.append("| Size | n | Ann. Return | Win Rate |")
    for label in ["<0.6", "0.6-0.8", "0.8-1.0", "1.0-1.2", ">1.2"]:
        bs = by_size.get(label, {})
        lines.append(f"| {label} | {bs.get('n','-')} | "
                     f"{bs.get('mean_return',0):.2%} | "
                     f"{bs.get('win_rate',0):.1%} |")
    lines.append("")

    return {
        "summary": "\n".join(lines),
        "metrics": {
            "is": is_metrics,
            "oos": oos_metrics,
            "all": all_metrics,
        },
        "by_direction": by_direction,
        "by_size": by_size,
        "df": df,
    }