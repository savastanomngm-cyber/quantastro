"""Full signal computation for every trading day — returns a DataFrame.

This is the production pipeline: feed it a date range, get back every signal
column per day.  Use --signals to dump CSV.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .aspects import find_all_aspects, detect_all_complex_patterns
from .bradley import bradley_index
from .ephemeris import PLANETS, get_longitudes, get_moon_phase, get_speeds, jd_from_date
from .midpoints import all_key_midpoint_hits, uranus_saturn_pluto, midpoint_scan
from .optimize import compute_confluence_score, stellium_volatility_signal


def _trading_days(start: str, end: str) -> List[str]:
    """Weekdays between start and end (inclusive)."""
    sd = datetime.strptime(start, "%Y-%m-%d")
    ed = datetime.strptime(end, "%Y-%m-%d")
    days = []
    curr = sd
    while curr <= ed:
        if curr.weekday() < 5:
            days.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)
    return days


def compute_signals_df(
    start: str,
    end: str,
    optimized_weights: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """Compute ALL astro signals for every weekday in the date range.

    Columns returned per day:
      date, moon_elongation, moon_illumination, moon_phase_label,
      merc_rx, venus_rx, mars_rx, jupiter_rx, saturn_rx, uranus_rx,
      neptune_rx, pluto_rx,
      hard_aspect_count, soft_aspect_count, aspect_count,
      stellium_flag, grand_cross_flag, t_square_flag, yod_flag,
      grand_trine_flag,
      stellium_vol_mult, stellium_bodies_count, stellium_sign,
      bradley_total, bradley_hard, bradley_soft,
      bradley_optimized (if weights provided),
      midpoint_hit_count, usp_hit_flag, usp_orb,
      confluence_score, confluence_bull_count, confluence_bear_count,
      confluence_interpretation, confluence_flags

    Args:
        start, end: "YYYY-MM-DD" date range
        optimized_weights: from optimize_bradley_weights() — if provided,
            a bradley_optimized column is added using learned weights
    """
    from .optimize import compute_optimized_bradley

    days = _trading_days(start, end)
    rows = []

    for date_str in days:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        jd = jd_from_date(dt.year, dt.month, dt.day, 12.0)
        pos = get_longitudes(jd)
        spd = get_speeds(jd)
        moon = get_moon_phase(jd)
        aspects = find_all_aspects(pos)
        cp = detect_all_complex_patterns(pos)
        bi = bradley_index(pos)
        hits = all_key_midpoint_hits(pos, orb=1.0)
        usp = uranus_saturn_pluto(pos, orb=2.0)
        st_vol = stellium_volatility_signal(pos)

        hard = sum(1 for a in aspects if a["type"] in ("conjunction", "square", "opposition"))
        soft = sum(1 for a in aspects if a["type"] in ("sextile", "trine"))

        elong = moon["elongation"]
        if elong <= 15 or elong >= 345:
            phase_label = "new"
        elif 165 <= elong <= 195:
            phase_label = "full"
        elif 90 <= elong <= 105:
            phase_label = "first_quarter"
        elif 255 <= elong <= 270:
            phase_label = "last_quarter"
        else:
            phase_label = ""

        conf = compute_confluence_score(pos, spd, cp, bi["total"], len(hits))

        row: Dict[str, Any] = {
            "date": date_str,
            # Moon
            "moon_elongation": round(elong, 2),
            "moon_illumination": round(moon["illumination"], 4),
            "moon_phase": phase_label,
            # Retrogrades
            "merc_rx": int(spd.get("Mercury", 0) < 0),
            "venus_rx": int(spd.get("Venus", 0) < 0),
            "mars_rx": int(spd.get("Mars", 0) < 0),
            "jupiter_rx": int(spd.get("Jupiter", 0) < 0),
            "saturn_rx": int(spd.get("Saturn", 0) < 0),
            "uranus_rx": int(spd.get("Uranus", 0) < 0),
            "neptune_rx": int(spd.get("Neptune", 0) < 0),
            "pluto_rx": int(spd.get("Pluto", 0) < 0),
            # Aspects
            "hard_aspect_count": hard,
            "soft_aspect_count": soft,
            "aspect_count": bi["aspect_count"],
            # Complex patterns
            "stellium_flag": int(cp.get("stellium") is not None),
            "grand_cross_flag": int(cp.get("grand_cross") is not None),
            "t_square_flag": int(cp.get("t_square") is not None),
            "yod_flag": int(cp.get("yod") is not None),
            "grand_trine_flag": int(cp.get("grand_trine") is not None),
            # Stellium volatility
            "stellium_vol_mult": st_vol["volatility_multiplier"] if st_vol else 1.0,
            "stellium_bodies_count": st_vol["bodies_count"] if st_vol else 0,
            "stellium_sign": st_vol.get("sign", "") if st_vol else "",
            # Bradley
            "bradley_total": bi["total"],
            "bradley_hard": bi["hard_sum"],
            "bradley_soft": bi["soft_sum"],
            # Midpoints
            "midpoint_hit_count": len(hits),
            "usp_hit_flag": int(usp is not None),
            "usp_orb": round(usp["orb"], 4) if usp else None,
            # Confluence
            "confluence_score": conf["score"],
            "confluence_bull_count": conf["bull_count"],
            "confluence_bear_count": conf["bear_count"],
            "confluence_interpretation": conf["interpretation"],
            "confluence_flags": "|".join(conf["flags"]),
        }

        # Optimized Bradley
        if optimized_weights:
            from .optimize import compute_optimized_bradley
            opt_val = compute_optimized_bradley(pos, optimized_weights)
            row["bradley_optimized"] = round(opt_val, 6)

        rows.append(row)

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def compute_signals_with_returns(
    start: str,
    end: str,
    ticker: str = "SPY",
    optimized_weights: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """Compute signals + fetch market data, return merged DataFrame.

    Columns: all signal columns from compute_signals_df() plus:
      close, log_return, return_pct, cum_return
    """
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError("yfinance not installed — pip install yfinance")

    signals = compute_signals_df(start, end, optimized_weights)

    data = yf.download(ticker, start=start, end=end, progress=False)
    if data.empty:
        raise ValueError(f"no yfinance data for {ticker}")

    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    price_df = pd.DataFrame({
        "date": pd.to_datetime(close.index),
        "close": close.values,
    })
    price_df["log_return"] = np.log(price_df["close"] / price_df["close"].shift(1))
    price_df["return_pct"] = price_df["close"].pct_change()
    price_df["cum_return"] = (1 + price_df["return_pct"]).cumprod() - 1.0

    merged = signals.merge(price_df, on="date", how="left")
    return merged


def signals_to_csv(
    start: str,
    end: str,
    ticker: str = "SPY",
    output_path: Optional[str] = None,
    optimized_weights: Optional[Dict[str, float]] = None,
) -> str:
    """Compute full signal + returns DataFrame and save to CSV.

    Returns the CSV as a string (first 2000 chars) and saves to output_path.
    """
    df = compute_signals_with_returns(start, end, ticker, optimized_weights)

    if output_path:
        df.to_csv(output_path, index=False, float_format="%.6f")
        return f"Saved {len(df)} rows × {len(df.columns)} cols → {output_path}\n\nColumns: {list(df.columns)}"

    # If no path, return preview
    preview = df.to_csv(index=False, float_format="%.4f")
    return f"{len(df)} rows × {len(df.columns)} cols\n\n{preview[:3000]}..."