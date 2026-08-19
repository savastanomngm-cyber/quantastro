"""Astro + golden-fib confluence detector.

When price is at a fib extreme (±1.372, ±1.272) AND specific astrological
conditions are met, the probability of reversal is elevated.  This module
scores each confluence event and provides Hitt/Weingarten-cited rationale.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .ephemeris import (
    PLANETS, get_longitudes, get_moon_phase, get_speeds, jd_from_date,
)
from .aspects import find_all_aspects, detect_all_complex_patterns
from .midpoints import all_key_midpoint_hits, uranus_saturn_pluto
from .fibrisk import FibEnvelope


# ── Recalibrated weights (SPY, 2018-2022, 5d forward return) ─────────
# Empirically fit via Ridge regression on 406 extreme events.
# Old weights were fixed ±1/±2/±3 from Hitt's qualitative importance.
# New weights are actual coefficients predicting 5-day return.
#
# Positive weight → fade the extreme (buy reversal)
# Negative weight → extreme may continue (don't fade)
#
# R² = 0.047 (modest), but quintile monotonicity is clean:
#   worst quintile: -0.33%  →  best quintile: +0.99%

RECALIBRATED_WEIGHTS = {
    "grand_cross":       +0.00995,
    "moon_phase_full":   -0.00694,
    "t_square":          -0.00606,
    "is_upper_extreme":  -0.00590,
    "min_aspect_orb":    -0.00480,
    "grand_trine":       +0.00420,
    "yod":               +0.00341,
    "hard_tight_count":  +0.00339,
    "moon_phase_new":    +0.00316,
    "dist_into_extreme": -0.00126,
    "jupiter_rx":        -0.00119,
    "midpoint_count":    +0.00101,
    "moon_saturn_closeness": +0.00097,
    "soft_total":        +0.00082,
    "saturn_rx":         +0.00055,
    "merc_rx":           +0.00031,
    "usp_hit":           -0.00005,
    "hard_total":        -0.00002,
}

from .ephemeris import (
    PLANETS, get_longitudes, get_moon_phase, get_speeds, jd_from_date,
)
from .aspects import find_all_aspects, detect_all_complex_patterns
from .midpoints import all_key_midpoint_hits, uranus_saturn_pluto
from .fibrisk import FibEnvelope


# ── confluence rules ───────────────────────────────────────────────────

def score_reversal_at_extreme(
    extreme: str,           # '+1.372' or '-1.372'
    top_aspects: List[Dict[str, Any]],
    complex_patterns: Dict[str, Any],
    midpoint_hits: List[Dict[str, Any]],
    usp_hit: bool,
    merc_rx: bool,
    saturn_rx: bool,
    moon_phase_label: str,
) -> Dict[str, Any]:
    """Score the probability that price reverses at the extreme.

    Returns {score_1_to_5, reasons, confidence, action}.
    """

    score = 0
    reasons: List[str] = []
    is_upper = extreme.startswith("+")

    # ── 1. Hard aspects at the extreme (Hitt: trend-change) ─────
    hard_at_extreme = [a for a in top_aspects
                       if a["type"] in ("square", "opposition") and a["orb"] <= 2.0]
    if len(hard_at_extreme) >= 2:
        score += 2
        ps = ", ".join(f"{a['p1']}/{a['p2']}" for a in hard_at_extreme[:3])
        reasons.append(f"+2: {len(hard_at_extreme)} hard aspects at tight orb ({ps})")
    elif len(hard_at_extreme) == 1:
        score += 1
        a = hard_at_extreme[0]
        reasons.append(f"+1: {a['p1']}-{a['p2']} {a['type']} orb {a['orb']:.1f}°")

    # ── 2. Moon-Saturn hard aspect (Hitt: "no new exposure") ────
    moon_saturn = [a for a in top_aspects
                   if {a['p1'], a['p2']} == {"Moon", "Saturn"}
                   and a["type"] in ("square", "opposition")]
    if moon_saturn:
        ms = moon_saturn[0]
        if ms["orb"] <= 1.0:
            score += 2
            reasons.append(f"+2: Moon-Saturn {ms['type']} EXACT (orb {ms['orb']:.2f}°) — Hitt: fear/restraint peak")
        elif ms["orb"] <= 3.0:
            score += 1
            reasons.append(f"+1: Moon-Saturn {ms['type']} active (orb {ms['orb']:.1f}°)")

    # ── 3. Mercury retrograde (Weingarten: false signals) ───────
    if merc_rx:
        score -= 1  # reduces confidence — whipsaws
        reasons.append("-1: Mercury Rx — false signals, lower conviction")

    # ── 4. Saturn retrograde (Weingarten: "reality check") ──────
    if saturn_rx:
        score += 1
        reasons.append("+1: Saturn Rx — reality check, fib levels respected")

    # ── 5. Grand Cross or T-Square (Hitt: chaotic, big reversals) ──
    if complex_patterns.get("grand_cross"):
        score += 2
        reasons.append("+2: GRAND CROSS — chaotic reversal zone")
    elif complex_patterns.get("t_square"):
        score += 1
        reasons.append("+1: T-SQUARE — focused stress, reversal likely")

    # ── 6. Uranus=Saturn/Pluto (Hitt #1 signal) ─────────────────
    if usp_hit:
        score += 3
        reasons.append("+3: URANUS=SATURN/PLUTO — Hitt's #1, major cycle inflection")

    # ── 7. Moon phase — full moon = momentum, new moon = exhaustion ──
    if moon_phase_label == "FULL":
        if is_upper:  # full moon at upper extreme = exhaustion of momentum
            score += 1
            reasons.append("+1: Full Moon at upper extreme — momentum exhaustion")
    if moon_phase_label == "NEW":
        score += 1  # new moon = fresh start either direction
        reasons.append("+1: New Moon — mean-reversion bias at extremes")

    # ── clamp & interpret ────────────────────────────────────────
    score = max(1, min(5, score))

    if score >= 4:
        confidence = "VERY HIGH — fade the extreme with conviction"
        action = "FADE" if is_upper else "BUY"
    elif score >= 3:
        confidence = "HIGH — fade likely, tighten stop if against"
        action = "FADE" if is_upper else "BUY"
    elif score >= 2:
        confidence = "MODERATE — wait for closer orb or additional signal"
        action = "WAIT" if is_upper else "WAIT"
    else:
        confidence = "LOW — insufficient confluence, trade technicals"
        action = "NO_TRADE"

    return {
        "extreme": extreme,
        "score": score,
        "confidence": confidence,
        "action": action,
        "reasons": reasons,
    }


def compute_confluence(
    date_str: str,
    env: FibEnvelope,
    current_price: float,
) -> Optional[Dict[str, Any]]:
    """Full confluence check: fib extreme + astro signals.

    Returns None if price is not at an extreme.  Otherwise returns the
    scored confluence dict.
    """
    extreme = env.is_at_extreme(current_price, pct=2.5)
    if extreme is None:
        return None

    from datetime import datetime
    dt = datetime.strptime(date_str, "%Y-%m-%d")
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

    result = score_reversal_at_extreme(
        extreme=extreme,
        top_aspects=sorted(aspects, key=lambda a: a["orb"])[:6],
        complex_patterns=cp,
        midpoint_hits=hits,
        usp_hit=usp is not None,
        merc_rx=spd.get("Mercury", 0) < 0,
        saturn_rx=spd.get("Saturn", 0) < 0,
        moon_phase_label=moon_label,
    )

    return result


def score_reversal_calibrated(
    extreme: str,
    top_aspects: List[Dict[str, Any]],
    complex_patterns: Dict[str, Any],
    midpoint_hits: List[Dict[str, Any]],
    usp_hit: bool,
    merc_rx: bool,
    saturn_rx: bool,
    jupiter_rx: bool,
    moon_phase_label: str,
    is_upper: bool,
    dist_into_extreme_pct: float = 0.0,
) -> Dict[str, Any]:
    """Score using recalibrated weights from Ridge regression.

    Returns {score_1_to_5, expected_return, reasons, action}.
    The 'score' is a quintile (0-4) of the predicted return.
    """
    w = RECALIBRATED_WEIGHTS

    # Compute feature values (same as recalibration input)
    moon_saturn_orb = 10.0
    for a in top_aspects:
        if {a["p1"], a["p2"]} == {"Moon", "Saturn"} and a["type"] in ("square", "opposition"):
            moon_saturn_orb = min(moon_saturn_orb, a["orb"])

    hard_tight = sum(1 for a in top_aspects if a["type"] in ("square", "opposition") and a["orb"] <= 2.0)
    soft = sum(1 for a in top_aspects if a["type"] in ("sextile", "trine"))
    hard = sum(1 for a in top_aspects if a["type"] in ("square", "opposition"))
    min_orb = min((a["orb"] for a in top_aspects), default=10.0)

    # Compute predicted return
    pred = 0.0
    pred += w.get("moon_saturn_closeness", 0) * max(0, 5.0 - moon_saturn_orb)
    pred += w.get("hard_tight_count", 0) * hard_tight
    pred += w.get("hard_total", 0) * hard
    pred += w.get("soft_total", 0) * soft
    pred += w.get("min_aspect_orb", 0) * min_orb
    pred += w.get("merc_rx", 0) * (1.0 if merc_rx else 0.0)
    pred += w.get("saturn_rx", 0) * (1.0 if saturn_rx else 0.0)
    pred += w.get("jupiter_rx", 0) * (1.0 if jupiter_rx else 0.0)
    pred += w.get("t_square", 0) * (1.0 if complex_patterns.get("t_square") else 0.0)
    pred += w.get("grand_cross", 0) * (1.0 if complex_patterns.get("grand_cross") else 0.0)
    pred += w.get("yod", 0) * (1.0 if complex_patterns.get("yod") else 0.0)
    pred += w.get("grand_trine", 0) * (1.0 if complex_patterns.get("grand_trine") else 0.0)
    pred += w.get("usp_hit", 0) * (1.0 if usp_hit else 0.0)
    pred += w.get("midpoint_count", 0) * len(midpoint_hits)
    pred += w.get("moon_phase_full", 0) * (1.0 if moon_phase_label == "FULL" else 0.0)
    pred += w.get("moon_phase_new", 0) * (1.0 if moon_phase_label == "NEW" else 0.0)
    pred += w.get("is_upper_extreme", 0) * (1.0 if is_upper else 0.0)
    pred += w.get("dist_into_extreme", 0) * dist_into_extreme_pct

    # Map to quintile based on the calibration bins
    # Bin boundaries from training: [-0.0033, +0.0003, +0.0052, +0.0099, +0.0099]
    if pred < -0.0015:
        score = 1
    elif pred < 0.0003:
        score = 2
    elif pred < 0.0052:
        score = 3
    elif pred < 0.0090:
        score = 4
    else:
        score = 5

    reasons = []
    # Contributing factors (positive drivers)
    drivers = []
    if complex_patterns.get("grand_cross"):
        drivers.append("Grand Cross (strongest positive)")
    if complex_patterns.get("grand_trine"):
        drivers.append("Grand Trine (continuation)")
    if hard_tight >= 2:
        drivers.append(f"{hard_tight} hard aspects at tight orb")
    if moon_phase_label == "NEW":
        drivers.append("New Moon (fresh start)")
    if moon_saturn_orb < 2.0:
        drivers.append(f"Moon-Saturn close (orb {moon_saturn_orb:.1f}°)")

    # Negative drivers
    neg_drivers = []
    if is_upper:
        neg_drivers.append("Upper extreme (historical edge is fade-lower, not fade-upper)")
    if moon_phase_label == "FULL":
        neg_drivers.append("Full Moon (momentum continues)")
    if complex_patterns.get("t_square"):
        neg_drivers.append("T-Square (stress extends)")
    if min_orb < 1.0:
        neg_drivers.append(f"Exact aspect at {min_orb:.1f}° (trend extends)")

    reasons = [f"+: {d}" for d in drivers] + [f"-: {d}" for d in neg_drivers]
    if not reasons:
        reasons = ["No strong directional signals"]

    if score >= 4:
        action = "FADE" if is_upper else "BUY"
        confidence = "HIGH — calibrated model predicts strong reversal"
    elif score >= 3:
        action = "FADE" if is_upper else "BUY"
        confidence = "MODERATE — calibrated model predicts mild reversal"
    elif score >= 2:
        action = "WAIT"
        confidence = "LOW — calibrated model predicts near-flat return"
    else:
        action = "NO_TRADE" if is_upper else "WAIT"
        confidence = "NEGATIVE — calibrated model predicts extension, not reversal"

    return {
        "extreme": extreme,
        "score": score,
        "predicted_return": round(pred, 6),
        "confidence": confidence,
        "action": action,
        "reasons": reasons,
    }


def render_confluence(conf: Optional[Dict[str, Any]]) -> str:
    """Format confluence result for the signal card."""
    if conf is None:
        return "  No fib extreme detected — price in normal range."

    stars = "★" * conf["score"] + "☆" * (5 - conf["score"])
    lines = [
        f"  FIB EXTREME: {conf['extreme']}  |  CONFLUENCE: {stars} ({conf['confidence']})",
        f"  Action: {conf['action']}",
    ]
    for r in conf["reasons"]:
        lines.append(f"    {r}")
    return "\n".join(lines)