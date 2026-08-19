"""Backtest / event-study harness.

Works with a user-supplied price DataFrame (e.g., from yfinance) plus
the computed astro-signal series.  Does NOT fetch price data itself — 
the user injects it.

Provides:
  - generate_signal_df(start_date, end_date) → pandas DataFrame of daily signals
  - analyze_signal(signal_df, price_df) → stats dict
  - event_study(event_dates, price_series, lookback, lookforward) → return profiles
  - z_score_analysis(signal_series, return_series) → conditional z-score tables
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .ephemeris import (
    PLANETS,
    get_longitudes,
    get_moon_phase,
    get_speeds,
    jd_from_date,
)
from .aspects import find_all_aspects, detect_all_complex_patterns
from .midpoints import all_key_midpoint_hits, uranus_saturn_pluto, midpoint_scan
from .bradley import bradley_index


def _trading_days(start: str, end: str) -> List[str]:
    """Generate a list of weekdays (Mon-Fri) between start and end dates."""
    sd = datetime.strptime(start, "%Y-%m-%d")
    ed = datetime.strptime(end, "%Y-%m-%d")
    days = []
    curr = sd
    while curr <= ed:
        if curr.weekday() < 5:  # Mon-Fri
            days.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)
    return days


def generate_signal_df(
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    """Generate a daily astro-signal series.

    Returns a list of dicts — convert to DataFrame with ``pd.DataFrame(rows)``.

    Columns per row:
      date, bradley_total, bradley_hard, bradley_soft, aspect_count,
      hard_aspect_count, soft_aspect_count, moon_elongation, moon_illumination,
      merc_rx, venus_rx, mars_rx, jupiter_rx, saturn_rx, uranus_rx,
      neptune_rx, pluto_rx, stellium_flag, grand_cross_flag, t_square_flag,
      yod_flag, grand_trine_flag, midpoint_hit_count, usp_hit_flag,
      usp_orb
    """
    days = _trading_days(start_date, end_date)
    rows = []
    for date_str in days:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        jd = jd_from_date(dt.year, dt.month, dt.day, 12.0)
        pos = get_longitudes(jd)
        speeds = get_speeds(jd)
        moon = get_moon_phase(jd)
        aspects = find_all_aspects(pos)
        cp = detect_all_complex_patterns(pos)
        bi = bradley_index(pos)
        hits = all_key_midpoint_hits(pos, orb=1.0)
        usp = uranus_saturn_pluto(pos, orb=2.0)

        hard_count = sum(1 for a in aspects if a["type"] in ("conjunction", "square", "opposition"))
        soft_count = sum(1 for a in aspects if a["type"] in ("sextile", "trine"))

        row = {
            "date": date_str,
            "bradley_total": bi["total"],
            "bradley_hard": bi["hard_sum"],
            "bradley_soft": bi["soft_sum"],
            "aspect_count": bi["aspect_count"],
            "hard_aspect_count": hard_count,
            "soft_aspect_count": soft_count,
            "moon_elongation": round(moon["elongation"], 2),
            "moon_illumination": round(moon["illumination"], 4),
            "merc_rx": 1 if speeds.get("Mercury", 0) < 0 else 0,
            "venus_rx": 1 if speeds.get("Venus", 0) < 0 else 0,
            "mars_rx": 1 if speeds.get("Mars", 0) < 0 else 0,
            "jupiter_rx": 1 if speeds.get("Jupiter", 0) < 0 else 0,
            "saturn_rx": 1 if speeds.get("Saturn", 0) < 0 else 0,
            "uranus_rx": 1 if speeds.get("Uranus", 0) < 0 else 0,
            "neptune_rx": 1 if speeds.get("Neptune", 0) < 0 else 0,
            "pluto_rx": 1 if speeds.get("Pluto", 0) < 0 else 0,
            "stellium_flag": 1 if cp.get("stellium") else 0,
            "grand_cross_flag": 1 if cp.get("grand_cross") else 0,
            "t_square_flag": 1 if cp.get("t_square") else 0,
            "yod_flag": 1 if cp.get("yod") else 0,
            "grand_trine_flag": 1 if cp.get("grand_trine") else 0,
            "midpoint_hit_count": len(hits),
            "usp_hit_flag": 1 if usp else 0,
            "usp_orb": round(usp["orb"], 4) if usp else None,
        }
        rows.append(row)
    return rows


def analyze_signal(
    signal_df,
    price_df,
    return_col: str = "log_return",
) -> Dict[str, Any]:
    """Correlate signal columns against a returns column.

    Args:
        signal_df: DataFrame from generate_signal_df (or with same columns)
        price_df: DataFrame with a DatetimeIndex and a returns column
        return_col: name of the returns column

    Returns:
        dict with correlation, t-stats, and conditional means for key signals.
    """
    df = signal_df.merge(
        price_df[[return_col]],
        left_on="date", right_index=True, how="inner",
    )
    if len(df) < 10:
        return {"error": "insufficient data points"}

    results: Dict[str, Any] = {
        "observations": len(df),
        "correlations": {},
        "conditional_means": {},
        "hit_rates": {},
    }

    signal_cols = [
        "bradley_total", "bradley_hard", "bradley_soft",
        "hard_aspect_count", "soft_aspect_count", "aspect_count",
        "moon_elongation", "merc_rx", "stellium_flag",
        "grand_cross_flag", "t_square_flag", "yod_flag",
        "grand_trine_flag", "usp_hit_flag", "midpoint_hit_count",
    ]

    for col in signal_cols:
        if col not in df.columns:
            continue
        mask = df[col].notna()
        if mask.sum() < 10:
            continue
        corr = df.loc[mask, col].corr(df.loc[mask, return_col])
        results["correlations"][col] = round(float(corr), 4)

        # Conditional mean when signal is "on" (for binary flags)
        if col.endswith("_flag") or col.endswith("_rx"):
            hit_returns = df.loc[mask & (df[col] == 1), return_col]
            miss_returns = df.loc[mask & (df[col] == 0), return_col]
            if len(hit_returns) > 2 and len(miss_returns) > 2:
                results["conditional_means"][col] = {
                    "when_active": round(float(hit_returns.mean()), 6),
                    "when_inactive": round(float(miss_returns.mean()), 6),
                    "hits": len(hit_returns),
                    "misses": len(miss_returns),
                }
                try:
                    from numpy import std, sqrt
                    diff = hit_returns.mean() - miss_returns.mean()
                    se = ((hit_returns.std()**2 / len(hit_returns)) +
                          (miss_returns.std()**2 / len(miss_returns))) ** 0.5
                    t_stat = diff / se if se > 0 else 0
                    results["conditional_means"][col]["t_stat"] = round(float(t_stat), 3)
                except Exception:
                    pass

    return results


def event_study(
    event_dates: List[str],
    price_series,
    lookback_days: int = 10,
    lookforward_days: int = 20,
) -> Dict[str, Any]:
    """Compute cumulative returns around event dates.

    Args:
        event_dates: list of "YYYY-MM-DD" strings (the event windows)
        price_series: pandas Series with DatetimeIndex, prices
        lookback_days: trading days before event
        lookforward_days: trading days after event

    Returns:
        dict with average cumulative return profile and raw profiles per event.
    """
    if not isinstance(price_series.index, __import__('pandas').DatetimeIndex):
        try:
            price_series.index = __import__('pandas').to_datetime(price_series.index)
        except Exception:
            return {"error": "price_series must have DatetimeIndex"}

    profiles = {}
    for ed in event_dates:
        try:
            evt = __import__('pandas').to_datetime(ed)
        except Exception:
            continue
        # find nearest trading day or the day itself
        idx = price_series.index.get_indexer([evt], method="nearest")
        if idx[0] < 0:
            continue
        evt_pos = idx[0]
        start = max(0, evt_pos - lookback_days)
        end = min(len(price_series), evt_pos + lookforward_days + 1)
        window = price_series.iloc[start:end]
        if len(window) < 2:
            continue
        # cumulative return from event day
        evt_price = price_series.iloc[evt_pos]
        cum_ret = (window / evt_price - 1.0).values
        profiles[ed] = {
            "cumret": cum_ret.tolist(),
            "offset": list(range(start - evt_pos, end - evt_pos)),
        }

    if not profiles:
        return {"error": "no events matched in price series"}

    # Average profile
    max_len = max(len(p["cumret"]) for p in profiles.values())
    avg_profile = np.zeros(max_len)
    count = np.zeros(max_len)
    for p in profiles.values():
        arr = np.array(p["cumret"])
        n = len(arr)
        avg_profile[:n] += arr
        count[:n] += 1
    avg_profile = avg_profile / np.maximum(count, 1)

    offsets = list(range(-lookback_days, lookforward_days + 1))
    # trim to actual length
    avg_profile = avg_profile[:len(offsets)]
    offsets = offsets[:len(avg_profile)]

    return {
        "n_events": len(profiles),
        "offsets": offsets,
        "avg_cumulative_return": [round(float(x), 6) for x in avg_profile],
        "profiles": profiles,
    }


def z_score_analysis(
    signal_series,
    return_series,
    n_bins: int = 10,
) -> Dict[str, Any]:
    """Bin a continuous signal into deciles and compute mean return per bin.

    Args:
        signal_series: pandas Series (same index as returns)
        return_series: pandas Series (same index as signal)
        n_bins: number of bins (default 10 for deciles)

    Returns:
        dict with bins and mean returns, plus monotonicity score.
    """
    aligned = __import__('pandas').concat([signal_series, return_series], axis=1).dropna()
    if len(aligned) < n_bins * 5:
        return {"error": "insufficient data for binning"}

    sig_col = aligned.columns[0]
    ret_col = aligned.columns[1]

    try:
        aligned["bin"] = __import__('pandas').qcut(aligned[sig_col], n_bins, labels=False, duplicates="drop")
    except Exception:
        return {"error": "binning failed — too few unique signal values"}

    grouped = aligned.groupby("bin")[ret_col].agg(["mean", "std", "count"])
    bins = []
    for b in sorted(grouped.index):
        row = grouped.loc[b]
        bins.append({
            "bin": int(b),
            "mean_return": round(float(row["mean"]), 6),
            "std": round(float(row["std"]), 6),
            "count": int(row["count"]),
        })

    # Monotonicity: correlation between bin rank and mean return
    means = [b["mean_return"] for b in bins]
    ranks = list(range(len(means)))
    if len(means) > 1:
        mono = np.corrcoef(ranks, means)[0, 1]
    else:
        mono = 0.0

    return {
        "bins": bins,
        "monotonicity_score": round(float(mono), 4),
        "interpretation": (
            "strong monotonic signal" if abs(mono) > 0.7
            else "moderate monotonic signal" if abs(mono) > 0.4
            else "weak or no monotonic pattern"
        ),
    }