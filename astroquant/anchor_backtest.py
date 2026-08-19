"""Grid backtest: test multiple anchor methods for the golden fib envelope.

Anchors tested:
  A. Previous day's full OHLC range (baseline)
  B. Previous day's range × 0.6 (proxy for morning range from full day)
  C. Previous day's range × 0.4 (conservative proxy)
  D. Previous day's ATR(14) × 0.5 (volatility-scaled)

For each anchor, a fib envelope is built from the previous day. Today's
close is checked against ±1.272 of that envelope. When an extreme is hit,
the astro confluence is scored. Forward returns are measured.

The winner is the anchor that produces the best fade-lower and fade-upper
hit rates with the clearest IS/OOS stability.
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


def _check_extreme(env: FibEnvelope, price: float) -> Tuple[Optional[str], float]:
    """Check if price is beyond ±1.272 of the envelope."""
    lvls = env.levels()
    up = lvls["+1.272"]
    dn = lvls["-1.272"]
    if price > up:
        return "+1.372", (price - up) / env.range_size * 100.0
    if price < dn:
        return "-1.372", (dn - price) / env.range_size * 100.0
    return None, 0.0


def grid_backtest(
    ticker: str = "SPY",
    start: str = "2018-01-01",
    end: str = "2026-08-01",
    forward_days: List[int] = [1, 2, 3, 5, 10],
) -> Dict[str, Any]:
    """Run all anchor methods and compare."""
    import yfinance as yf

    data = yf.download(ticker, start=start, end=end, progress=False)
    if data.empty:
        return {"error": f"no data for {ticker}"}

    close = np.array([float(x) for x in data[("Close", ticker)]])
    high  = np.array([float(x) for x in data[("High", ticker)]])
    low   = np.array([float(x) for x in data[("Low", ticker)]])
    open_ = np.array([float(x) for x in data[("Open", ticker)]])
    dates = data.index

    # ── ATR(14) for volatility anchor ──
    tr = np.maximum(high - low,
                    np.maximum(abs(high - np.roll(close, 1)),
                               abs(low - np.roll(close, 1))))
    atr14 = np.zeros(len(close))
    for i in range(14, len(close)):
        atr14[i] = np.mean(tr[i-13:i+1])

    # ── Anchor configs ──
    anchors = {
        "A_prev_full":   lambda i: (open_[i-1], high[i-1], low[i-1], close[i-1], 1.0),
        "B_prev_0.6":    lambda i: (open_[i-1], high[i-1], low[i-1], close[i-1], 0.6),
        "C_prev_0.4":    lambda i: (open_[i-1], high[i-1], low[i-1], close[i-1], 0.4),
        "D_atr_half":    lambda i: (open_[i-1], close[i-1] + atr14[i-1]*0.5,
                                     close[i-1] - atr14[i-1]*0.5, close[i-1], 1.0),
    }

    results: Dict[str, Dict[str, Any]] = {}
    all_events: Dict[str, List[Dict]] = {}

    for name, anchor_fn in anchors.items():
        events = []
        for i in range(1, len(data)):
            if i < 15:  # need ATR
                continue
            try:
                a_o, a_h, a_l, a_c, scale = anchor_fn(i)
                if scale < 1.0:
                    # Shrink range around midpoint
                    mid = (a_h + a_l) / 2.0
                    half_R = (a_h - a_l) / 2.0 * scale
                    a_h = mid + half_R
                    a_l = mid - half_R
            except Exception:
                continue

            today_c = close[i]
            R = a_h - a_l
            if R <= 0 or np.isnan(R):
                continue

            env = FibEnvelope(
                anchor=(a_o + a_c) / 2,
                range_high=a_h,
                range_low=a_l,
                direction="long" if today_c > a_o else "short",
            )

            extreme, dist_pct = _check_extreme(env, today_c)
            if extreme is None:
                continue

            dt = dates[i]
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
                extreme=extreme,
                top_aspects=sorted(aspects, key=lambda a: a["orb"])[:6],
                complex_patterns=cp,
                midpoint_hits=hits,
                usp_hit=usp is not None,
                merc_rx=spd.get("Mercury", 0) < 0,
                saturn_rx=spd.get("Saturn", 0) < 0,
                moon_phase_label=moon_label,
            )

            fwd_rets = {}
            for fd in forward_days:
                if i + fd < len(data):
                    fwd_rets[f"fwd_{fd}d"] = (close[i + fd] - today_c) / today_c

            events.append({
                "date": date_str,
                "extreme": extreme,
                "dist_pct": round(dist_pct, 2),
                "confluence_score": conf["score"],
                "t_square": int(cp.get("t_square") is not None),
                "grand_cross": int(cp.get("grand_cross") is not None),
                "hard_aspects": sum(1 for a in aspects if a["type"] in ("square", "opposition")),
                "moon_phase": moon_label,
                **fwd_rets,
            })

        if not events:
            results[name] = {"error": "no events"}
            continue

        df = pd.DataFrame(events)

        # Split
        split_date = "2022-01-01"
        is_df = df[df["date"] < split_date]
        oos_df = df[df["date"] >= split_date]

        def stats(subset: pd.DataFrame, label: str) -> dict:
            if len(subset) == 0:
                return {"label": label, "n": 0}
            s = {"label": label, "n": len(subset)}
            for fd in forward_days:
                col = f"fwd_{fd}d"
                if col in subset.columns:
                    v = subset[col].dropna()
                    s[f"{col}_mean"] = round(float(v.mean()), 6)
                    s[f"{col}_hit"] = round(float((v > 0).mean()), 4)

            upper = subset[subset["extreme"] == "+1.372"]
            lower = subset[subset["extreme"] == "-1.372"]
            for fd in forward_days:
                col = f"fwd_{fd}d"
                if col not in subset.columns:
                    continue
                if len(upper) > 2:
                    u = upper[col].dropna()
                    # Fade upper = want negative returns → check (-ret > 0)
                    s[f"fade_upper_{fd}d"] = round(float((-u > 0).mean()), 4)
                if len(lower) > 2:
                    l = lower[col].dropna()
                    s[f"fade_lower_{fd}d"] = round(float((l > 0).mean()), 4)

            # By confluence
            by_score = {}
            for sc in sorted(subset["confluence_score"].unique()):
                ss = subset[subset["confluence_score"] == sc]
                if len(ss) < 3:
                    continue
                entry = {"n": len(ss)}
                for fd in forward_days:
                    col = f"fwd_{fd}d"
                    if col in ss.columns:
                        v = ss[col].dropna()
                        entry[f"{col}_mean"] = round(float(v.mean()), 6)
                by_score[str(sc)] = entry
            s["by_score"] = by_score
            return s

        results[name] = {
            "total": len(df),
            "is": stats(is_df, "IS"),
            "oos": stats(oos_df, "OOS"),
            "all": stats(df, "ALL"),
        }
        all_events[name] = events

    # ── Scoreboard ──
    def score_anchor(name: str, r: dict) -> dict:
        """Compute a composite score for an anchor method."""
        is_s = r.get("is", {})
        oos_s = r.get("oos", {})
        score_val = 0.0

        # Fade-lower 5d OOS hit rate is the primary metric
        fl5_ois = is_s.get("fade_lower_5d", 0)
        fl5_oos = oos_s.get("fade_lower_5d", 0)
        fl5_both = (fl5_ois + fl5_oos) / 2.0 if fl5_ois and fl5_oos else 0

        # Fade-upper 5d (we DON'T want this to be >50% — it's negative edge)
        fu5_oos = oos_s.get("fade_upper_5d", 0)

        # OOS stability: how close is OOS to IS?
        stability_penalty = abs(fl5_ois - fl5_oos) * 100

        score_val = fl5_both * 100  # 65% → 65 points
        score_val -= stability_penalty * 2  # 5% gap → -10 points
        if fu5_oos > 0.55:  # upper-fade works? that's actually bad for the signal
            pass  # but it's interesting

        return {
            "fade_lower_5d_IS": round(fl5_ois * 100, 1),
            "fade_lower_5d_OOS": round(fl5_oos * 100, 1),
            "fade_upper_5d_OOS": round(fu5_oos * 100, 1),
            "stability_gap": round(abs(fl5_ois - fl5_oos) * 100, 1),
            "composite": round(score_val, 1),
            "n_events": r.get("total", 0),
        }

    scoreboard = {name: score_anchor(name, r) for name, r in results.items() if "error" not in r}

    # ── Markdown summary ──
    lines = [f"## Golden Fib Anchor Grid Backtest: {ticker}"]
    lines.append(f"**Period:** {start} → {end} | **Split:** 2022-01-01")
    lines.append("")
    lines.append("| Anchor | n | Fade-Low IS | Fade-Low OOS | Gap | Fade-Up OOS | Score |")
    lines.append("|--------|---|-------------|--------------|-----|-------------|-------|")
    best = None
    for name in ["A_prev_full", "B_prev_0.6", "C_prev_0.4", "D_atr_half"]:
        sb = scoreboard.get(name, {})
        fl_is = f"{sb.get('fade_lower_5d_IS',0):.0f}%"
        fl_oo = f"{sb.get('fade_lower_5d_OOS',0):.0f}%"
        fu_oo = f"{sb.get('fade_upper_5d_OOS',0):.0f}%"
        gap = f"{sb.get('stability_gap',0):.1f}"
        score = f"{sb.get('composite',0):.1f}"
        n = sb.get("n_events", 0)
        lines.append(f"| {name} | {n} | {fl_is} | {fl_oo} | {gap} | {fu_oo} | {score} |")
        if not best or sb.get("composite", 0) > scoreboard[best].get("composite", 0):
            best = name
    lines.append("")

    # Best anchor detail
    if best and best in results and "error" not in results[best]:
        r = results[best]
        lines.append(f"### Best Anchor: **{best}**")
        for subset, label in [(r["is"], "IN-SAMPLE"), (r["oos"], "OUT-OF-SAMPLE")]:
            lines.append(f"**{label}** (n={subset['n']})")
            for fd in forward_days:
                col = f"fwd_{fd}d"
                if col + "_mean" in subset:
                    lines.append(f"- Fwd {fd}d: mean {subset[col+'_mean']:+.4%} hit {subset.get(col+'_hit',0):.1%}")
            lines.append(f"- Fade-lower: 1d={subset.get('fade_lower_1d',0):.1%} "
                         f"3d={subset.get('fade_lower_3d',0):.1%} "
                         f"5d={subset.get('fade_lower_5d',0):.1%} "
                         f"10d={subset.get('fade_lower_10d',0):.1%}")
            lines.append("")

    return {
        "scoreboard": scoreboard,
        "results": results,
        "best_anchor": best,
        "summary": "\n".join(lines),
    }