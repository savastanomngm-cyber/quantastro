"""Backtest the golden fib + astro confluence strategy.

Uses the PREVIOUS day's range as the envelope anchor for today.
Yesterday's OHLC creates the fib grid; today's close is checked against
±1.272 of that grid.  When extreme + astro confluence align, forward
returns are measured to test the reversal hypothesis.

In live trading: morning range (first 30-60 min) replaces yesterday's range.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .ephemeris import get_longitudes, get_moon_phase, get_speeds, jd_from_date
from .aspects import find_all_aspects, detect_all_complex_patterns
from .midpoints import all_key_midpoint_hits, uranus_saturn_pluto
from .fibrisk import FibEnvelope
from .confluence import score_reversal_at_extreme


def _fib_zone_from_yesterday(
    prev_o: float, prev_h: float, prev_l: float, prev_c: float,
    today_c: float,
) -> Tuple[Optional[str], float, Optional[str], float]:
    """Build envelope from yesterday's OHLC, check if today's close is at extreme.

    Returns (upper_zone_or_None, pct_above_1272, lower_zone_or_None, pct_below_n1272).
    """
    env = FibEnvelope(
        anchor=(prev_o + prev_c) / 2,
        range_high=prev_h,
        range_low=prev_l,
        direction="long" if prev_c > prev_o else "short",
    )
    lvls = env.levels()
    R = env.range_size

    up_1272 = lvls["+1.272"]
    dn_1272 = lvls["-1.272"]

    upper_zone = "+1.372" if today_c > up_1272 else None
    upper_pct = (today_c - up_1272) / R * 100.0

    lower_zone = "-1.372" if today_c < dn_1272 else None
    lower_pct = (dn_1272 - today_c) / R * 100.0

    return upper_zone, upper_pct, lower_zone, lower_pct


def run_fib_backtest(
    ticker: str = "SPY",
    start: str = "2018-01-01",
    end: str = "2026-08-01",
    forward_days: List[int] = [1, 2, 3, 5, 10],
) -> Dict[str, Any]:
    """Full backtest: for every day, compute fib extremes + astro confluence,
    track forward returns at each confluence score level.

    Returns dict with summary stats and a DataFrame of all extreme events.
    """
    import yfinance as yf

    data = yf.download(ticker, start=start, end=end, progress=False)
    if data.empty:
        return {"error": f"no data for {ticker}"}

    close = data[("Close", ticker)]
    high = data[("High", ticker)]
    low = data[("Low", ticker)]
    open_ = data[("Open", ticker)]

    events = []
    dates = data.index

    for i in range(1, len(data)):  # start from 1 — need yesterday
        dt = dates[i]
        prev_dt = dates[i - 1]
        p_o, p_h, p_l, p_c = (
            float(open_.iloc[i - 1]), float(high.iloc[i - 1]),
            float(low.iloc[i - 1]), float(close.iloc[i - 1]),
        )
        today_c = float(close.iloc[i])
        R = p_h - p_l
        if R <= 0:
            continue

        # ── fib zone from yesterday's range ──
        up_zone, up_pct, dn_zone, dn_pct = _fib_zone_from_yesterday(p_o, p_h, p_l, p_c, today_c)

        for extreme_name, dist in [(up_zone, up_pct), (dn_zone, dn_pct)]:
            if extreme_name is None:
                continue

            date_str = dt.strftime("%Y-%m-%d")
            jd = jd_from_date(dt.year, dt.month, dt.day, 12.0)
            pos = get_longitudes(jd)
            spd = get_speeds(jd)
            moon = get_moon_phase(jd)
            aspects = find_all_aspects(pos)
            cp = detect_all_complex_patterns(pos)
            hits = all_key_midpoint_hits(pos, orb=1.0)
            usp = uranus_saturn_pluto(pos, orb=2.0)

            elong = moon["elongation"]
            moon_label = ("FULL" if 165 <= elong <= 195
                          else "NEW" if elong <= 15 or elong >= 345
                          else "")

            conf = score_reversal_at_extreme(
                extreme=extreme_name,
                top_aspects=sorted(aspects, key=lambda a: a["orb"])[:6],
                complex_patterns=cp,
                midpoint_hits=hits,
                usp_hit=usp is not None,
                merc_rx=spd.get("Mercury", 0) < 0,
                saturn_rx=spd.get("Saturn", 0) < 0,
                moon_phase_label=moon_label,
            )

            # Forward returns
            fwd_rets = {}
            for fd in forward_days:
                if i + fd < len(data):
                    fwd_close = float(close.iloc[i + fd])
                    fwd_rets[f"fwd_{fd}d"] = (fwd_close - today_c) / today_c

            events.append({
                "date": date_str,
                "extreme": extreme_name,
                "dist_pct": round(dist, 2),
                "confluence_score": conf["score"],
                "confidence": conf["confidence"],
                "action": conf["action"],
                "moon_phase": moon_label,
                "hard_aspects": sum(1 for a in aspects if a["type"] in ("square", "opposition")),
                "merc_rx": int(spd.get("Mercury", 0) < 0),
                "usp_hit": int(usp is not None),
                "t_square": int(cp.get("t_square") is not None),
                "prev_open": p_o, "prev_high": p_h, "prev_low": p_l, "prev_close": p_c,
                "today_close": today_c,
                "prev_range_pct": R / p_c * 100,
                **fwd_rets,
            })

    if not events:
        return {"error": "no extreme touches found"}

    df = pd.DataFrame(events)
    df["date"] = pd.to_datetime(df["date"])

    # ── split train/test ──
    split_date = "2022-01-01"
    train = df[df["date"] < split_date]
    test = df[df["date"] >= split_date]

    # ── analyze by confluence score ──
    def analyze_split(subset: pd.DataFrame, label: str) -> Dict[str, Any]:
        if len(subset) == 0:
            return {"label": label, "n": 0}

        result: Dict[str, Any] = {"label": label, "n": len(subset)}

        for fd in forward_days:
            col = f"fwd_{fd}d"
            if col not in subset.columns:
                continue
            valid = subset[col].dropna()
            if len(valid) == 0:
                continue
            mean_ret = float(valid.mean())
            hit_rate = float((valid > 0).mean())
            result[f"{col}_mean"] = round(mean_ret, 6)
            result[f"{col}_hit_rate"] = round(hit_rate, 4)

        # By confluence score
        by_score = {}
        for score in sorted(subset["confluence_score"].unique()):
            sdf = subset[subset["confluence_score"] == score]
            if len(sdf) < 3:
                continue
            score_stats = {"n": len(sdf)}
            for fd in forward_days:
                col = f"fwd_{fd}d"
                if col in sdf.columns:
                    valid = sdf[col].dropna()
                    if len(valid) >= 2:
                        score_stats[f"{col}_mean"] = round(float(valid.mean()), 6)
                        score_stats[f"{col}_hit_rate"] = round(float((valid > 0).mean()), 4)
            by_score[str(score)] = score_stats
        result["by_score"] = by_score

        # Direction check: did fading the extreme work?
        # Upper extreme (+1.372): fade = go SHORT → want negative forward return
        # Lower extreme (-1.372): fade = go LONG → want positive forward return
        upper = subset[subset["extreme"] == "+1.372"]
        lower = subset[subset["extreme"] == "-1.372"]
        for fd in forward_days:
            col = f"fwd_{fd}d"
            if col not in subset.columns:
                continue
            if len(upper) > 2:
                # Fade = short → want negative returns
                u_valid = upper[col].dropna()
                fade_upper_hit = float((-u_valid > 0).mean())
                result[f"fade_upper_{fd}d_hit"] = round(fade_upper_hit, 4)
            if len(lower) > 2:
                # Fade = buy → want positive returns
                l_valid = lower[col].dropna()
                fade_lower_hit = float((l_valid > 0).mean())
                result[f"fade_lower_{fd}d_hit"] = round(fade_lower_hit, 4)

        return result

    train_stats = analyze_split(train, "IN-SAMPLE (2018-2021)")
    test_stats = analyze_split(test, "OUT-OF-SAMPLE (2022-2026)")
    all_stats = analyze_split(df, "ALL (2018-2026)")

    # ── text summary ──
    lines = [f"## Golden Fib + Astro Confluence Backtest: {ticker}"]
    lines.append(f"**Period:** {start} → {end}")
    lines.append(f"**Total extreme touches:** {len(df)}")
    lines.append(f"**In-sample:** {len(train)} | **OOS:** {len(test)}")
    lines.append("")

    for stats, name in [(train_stats, "IN-SAMPLE"), (test_stats, "OOS"), (all_stats, "ALL")]:
        lines.append(f"### {name}")
        if stats["n"] == 0:
            lines.append("  No events.")
        else:
            lines.append(f"  n={stats['n']} events")
            for fd in forward_days:
                col = f"fwd_{fd}d"
                if col + "_mean" in stats:
                    lines.append(f"  Forward {fd}d: mean {stats[col+'_mean']:+.4%}  |  "
                                 f"hit rate {stats.get(col+'_hit_rate',0):.1%}")
            if "fade_upper_1d_hit" in stats:
                lines.append(f"  Fade-upper hit: 1d={stats.get('fade_upper_1d_hit',0):.1%}  "
                             f"3d={stats.get('fade_upper_3d_hit',0):.1%}  "
                             f"5d={stats.get('fade_upper_5d_hit',0):.1%}")
            if "fade_lower_1d_hit" in stats:
                lines.append(f"  Fade-lower hit: 1d={stats.get('fade_lower_1d_hit',0):.1%}  "
                             f"3d={stats.get('fade_lower_3d_hit',0):.1%}  "
                             f"5d={stats.get('fade_lower_5d_hit',0):.1%}")

            if "by_score" in stats and stats["by_score"]:
                lines.append("")
                lines.append("  By confluence score:")
                lines.append(f"  {'Score':<6} {'n':<5} {'1d mean':<10} {'3d mean':<10} {'5d mean':<10} {'10d mean':<10}")
                for score_key in sorted(stats["by_score"].keys(), key=int):
                    bs = stats["by_score"][score_key]
                    fd1 = bs.get("fwd_1d_mean", 0)
                    fd3 = bs.get("fwd_3d_mean", 0)
                    fd5 = bs.get("fwd_5d_mean", 0)
                    fd10 = bs.get("fwd_10d_mean", 0)
                    lines.append(f"  {score_key:<6} {bs['n']:<5} {fd1:+.4%}    {fd3:+.4%}    {fd5:+.4%}    {fd10:+.4%}")
        lines.append("")

    return {
        "ticker": ticker,
        "events_df": df,
        "train_stats": train_stats,
        "test_stats": test_stats,
        "all_stats": all_stats,
        "summary": "\n".join(lines),
    }