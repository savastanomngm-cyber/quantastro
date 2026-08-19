"""Pruned rulebook — position-sizing layer.

Encodes the Tier-1/Tier-2 discipline from astro12.py, fixed and wired
into the astroquant engine.  Produces a per-day output dict with
direction, size multiplier, and context.

Tier 1: changes position size (tested signals only)
Tier 2: monitor/watchlist only (no size change)

Sources: Hitt *AstroEcon*, Weingarten *Investing by the Stars*,
fib backtest results (fade-lower: 64% OOS, fade-upper: negative edge).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .ephemeris import PLANETS, get_longitudes, get_moon_phase, get_sign, get_speeds, jd_from_date
from .aspects import find_all_aspects, detect_all_complex_patterns
from .midpoints import all_key_midpoint_hits, uranus_saturn_pluto
from .fibrisk import FibEnvelope
from .confluence import score_reversal_calibrated


# ── Asset config ──────────────────────────────────────────────────────

ASSETS: Dict[str, Dict[str, Any]] = {
    "NQ": {
        "name": "Nasdaq 100 (NQ)",
        "rulers": ["Mercury", "Mars"],
        "co_rulers": ["Moon", "Jupiter"],
    },
    "ES": {
        "name": "S&P 500 (ES)",
        "rulers": ["Jupiter", "Saturn"],
        "co_rulers": ["Sun", "Moon"],
    },
    "GC": {
        "name": "Gold (GC)",
        "rulers": ["Sun", "Saturn"],
        "co_rulers": ["Venus", "Pluto"],
    },
}


# ── Planet speed helper ───────────────────────────────────────────────

def _is_rx(speeds: Dict[str, float], planet: str) -> bool:
    """Planet is retrograde: geocentric longitude speed is negative."""
    if planet not in speeds:
        return False
    return speeds[planet] < 0.0


# ── Tier-1 tilts (backtest-able) ──────────────────────────────────────

def tier1_tilts(
    pos: Dict[str, float],
    spd: Dict[str, float],
    moon_sign: str,
    moon_phase_label: str,
    asset: str,
    fib_signal: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Tier-1: signals that change position size.

    Only signals with backtest evidence are included.
    Weights are based on the historical hit rates from the fib backtest
    and the recalibrated confluence model.

    Returns {size_mult, tilts_list}.
    """
    size = 1.0
    tilts: List[str] = []

    # ── Fib extreme + calibrated confluence (strongest signal) ──
    if fib_signal:
        score = fib_signal.get("score", 0)
        extreme = fib_signal.get("extreme", "")
        if extreme == "-1.372" and score >= 4:
            # Fade-lower with strong confluence: IS 68%, OOS 64%
            size *= 1.30
            tilts.append(f"🥇 FIB LOWER STRONG ({score}/5): buy dip, size ×1.30 "
                         f"(backtest: 64% OOS hit rate)")
        elif extreme == "-1.372" and score >= 2:
            size *= 1.15
            tilts.append(f"🥈 FIB LOWER MODERATE ({score}/5): buy dip, size ×1.15")
        elif extreme == "+1.372":
            # Upper extreme: negative edge in backtest
            size *= 0.75
            tilts.append(f"⚠️ FIB UPPER ({score}/5): reduce size to ×0.75 "
                         f"(backtest: upper fade has negative edge)")

    # ── Moon-Saturn exact (Hitt: "no new exposure") ──
    aspects = find_all_aspects(pos)
    moon_saturn = [a for a in aspects
                   if {a["p1"], a["p2"]} == {"Moon", "Saturn"}
                   and a["type"] in ("square", "opposition")]
    if moon_saturn:
        ms = moon_saturn[0]
        if ms["orb"] <= 1.0:
            size *= 0.60
            tilts.append(f"🛑 Moon-Saturn EXACT (orb {ms['orb']:.2f}°): "
                         f"no new exposure, size ×0.60 (Hitt Lesson 10)")
        elif ms["orb"] <= 3.0:
            size *= 0.80
            tilts.append(f"⚠️ Moon-Saturn active (orb {ms['orb']:.1f}°): size ×0.80")

    # ── Uranus=Saturn/Pluto (Hitt #1: major cycle inflection) ──
    from .midpoints import uranus_saturn_pluto
    usp = uranus_saturn_pluto(pos, orb=2.0)
    if usp:
        size *= 0.70
        tilts.append(f"🔴 URANUS=SATURN/PLUTO (orb {usp['orb']:.3f}°): "
                     f"major cycle inflection, reduce size ×0.70 "
                     f"(Hitt #1 signal — historical: 1776/1852/1929/1997)")

    # ── Complex patterns ──
    cp = detect_all_complex_patterns(pos)
    if cp.get("grand_cross"):
        size *= 0.50
        tilts.append("🔴 GRAND CROSS: chaotic, size ×0.50 (tight stops)")
    if cp.get("stellium"):
        from .optimize import stellium_volatility_signal
        st = stellium_volatility_signal(pos)
        if st:
            mult = st["suggested_position_fraction"]
            size *= mult
            tilts.append(f"🔴 STELLIUM ({st['bodies_count']} bodies): "
                         f"volatility {st['volatility_multiplier']}×, size ×{mult:.0%}")

    size = max(0.40, min(1.50, size))

    return {
        "size_multiplier": round(size, 2),
        "tilts": tilts,
    }


# ── Tier-2 context (monitor only) ─────────────────────────────────────

def tier2_context(
    pos: Dict[str, float],
    spd: Dict[str, float],
    moon_sign: str,
    moon_phase_label: str,
    asset: str,
    prev_high: Optional[float] = None,
    prev_low: Optional[float] = None,
    prev_close: Optional[float] = None,
) -> Dict[str, Any]:
    """Tier-2: signals to monitor but not size to.

    Returns {context_list, watchlist}.
    """
    context: List[str] = []
    watchlist: List[str] = []

    # Mercury Rx: regime-dependent, not always negative
    if _is_rx(spd, "Mercury"):
        context.append("👀 Mercury Rx — whipsaw risk, tighter stops")

    # Moon phase context
    if moon_phase_label == "FULL":
        context.append("👀 Full Moon — momentum bias, trend-following flavour")
    elif moon_phase_label == "NEW":
        context.append("👀 New Moon — mean-reversion bias, fade extremes")

    # Ruler culminations (watchlist only — hypothesis, no sizing)
    # (This would need intraday data — placeholder for live mode)

    # Fib envelope context (if prev day data available)
    if prev_high and prev_low and prev_close:
        env = FibEnvelope(
            anchor=prev_close,
            range_high=prev_high,
            range_low=prev_low,
            direction="long",
        )
        lvls = env.levels()
        context.append(f"👀 Fib grid from yesterday: "
                       f"+1.372={lvls['+1.372']:.1f} "
                       f"-1.372={lvls['-1.372']:.1f}")

        # Check if yesterday's close was near an extreme (momentum into today)
        yesterday_extreme = env.is_at_extreme(prev_close, pct=4.0)
        if yesterday_extreme:
            context.append(f"⚠️ Yesterday closed at {yesterday_extreme} — "
                           f"watch for reversal follow-through")

    return {
        "context": context,
        "watchlist": watchlist,
    }


# ── Full rulebook output  (SIMPLIFIED for backtest: use same logic as fib backtest) ──

def rulebook_output(
    date_str: str,
    asset: str,
    prev_open: Optional[float] = None,
    prev_high: Optional[float] = None,
    prev_low: Optional[float] = None,
    prev_close: Optional[float] = None,
    current_close: Optional[float] = None,
) -> Dict[str, Any]:
    from datetime import datetime
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    jd = jd_from_date(dt.year, dt.month, dt.day, 12.0)

    pos = get_longitudes(jd)
    spd = get_speeds(jd)
    moon = get_moon_phase(jd)
    moon_sign, _, _ = get_sign(pos["Moon"])

    elong = moon["elongation"]
    phase_label = ("FULL" if 165 <= elong <= 195
                   else "NEW" if elong <= 15 or elong >= 345
                   else "")

    # ── Fib extreme detection (same logic as backtest) ──
    fib_extreme = None
    fib_confluence = None
    if current_close and prev_high and prev_low and prev_open:
        R = prev_high - prev_low
        if R > 0:
            env = FibEnvelope(
                anchor=(prev_open + prev_close) / 2 if prev_close else prev_high,
                range_high=prev_high,
                range_low=prev_low,
                direction="long",
            )
            lvls = env.levels()
            up = lvls["+1.272"]
            dn = lvls["-1.272"]

            if current_close > up:
                fib_extreme = "+1.372"
            elif current_close < dn:
                fib_extreme = "-1.372"

            if fib_extreme:
                aspects = find_all_aspects(pos)
                cp = detect_all_complex_patterns(pos)
                hits = all_key_midpoint_hits(pos, orb=1.0)
                usp = uranus_saturn_pluto(pos, orb=2.0)
                _, _, dist_pct = env.nearest_level(current_close)

                fib_confluence = score_reversal_calibrated(
                    extreme=fib_extreme,
                    top_aspects=sorted(aspects, key=lambda a: a["orb"])[:6],
                    complex_patterns=cp,
                    midpoint_hits=hits,
                    usp_hit=usp is not None,
                    merc_rx=_is_rx(spd, "Mercury"),
                    saturn_rx=_is_rx(spd, "Saturn"),
                    jupiter_rx=_is_rx(spd, "Jupiter"),
                    moon_phase_label=phase_label,
                    is_upper=fib_extreme.startswith("+"),
                    dist_into_extreme_pct=dist_pct,
                )

    # ── Direction from fib extreme ──
    direction = "NEUTRAL"
    if fib_extreme == "-1.372":
        direction = "LONG"
    elif fib_extreme == "+1.372":
        direction = "SHORT"

    # ── Size from tier-1 tilts ──
    t1 = tier1_tilts(pos, spd, moon_sign, phase_label, asset, fib_confluence)
    t2 = tier2_context(pos, spd, moon_sign, phase_label, asset,
                       prev_high, prev_low, prev_close)

    return {
        "date": date_str,
        "asset": asset,
        "direction": direction,
        "size_multiplier": t1["size_multiplier"],
        "tier1_tilts": t1["tilts"],
        "tier2_context": t2["context"],
        "fib_extreme": fib_extreme,
        "fib_confluence": fib_confluence,
        "moon_sign": moon_sign,
        "moon_phase": phase_label,
        "mercury_rx": _is_rx(spd, "Mercury"),
        "saturn_rx": _is_rx(spd, "Saturn"),
    }