"""Bradley-style weighted daily aspect sum.

From Donald Bradley (*Stock Market Prediction*, 1947), refined by Arch
Crawford and recounted in Robert Hitt's *AstroEcon*.

Core idea: assign a signed weight to every planetary pair based on the
angular aspect they form on a given day, then sum across all pairs.  The
result is a single scalar — the "sidereal potential projection line" —
which the market has historically tracked.

Crawford's improvement (the "Astronomic Cycles Sum"): use the actual
*historical average return* for each aspect as the weight, rather than
a theoretical value.  This module provides both variants.

Hitt's recounting (Lesson 7 context, quoting Crawford):
  "One happy result was ... perhaps the best timing-tracking services ...
  Crawford Perspectives rated No. 1"

Arch Crawford tracked the Astronomic Cycles Sum through the 1987 crash
and consistently found that major market moves aligned with the line.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .ephemeris import PLANETS, angle_diff
from .aspects import ASPECT_ANGLES


# ── Theoretical Bradley weights (from Bradley's original formulation) ──

# The classic weights: conjunction and opposition get strongest weight,
# sextile/trine are mildly positive, square is negative.
# Sign assignment is per traditional Bradley (not per-planet).
BRADLEY_WEIGHTS: Dict[str, float] = {
    "conjunction": 3.0,
    "sextile": 2.0,
    "square": -2.0,
    "trine": 1.0,
    "opposition": -1.5,
}

# ── Hard/Soft classification (Hitt overlay) ────────────────────────────

# Hitt distinguishes hard aspects (trend-change) vs soft (continuation).
# For the hybrid Hitt-Bradley version, we split the sum:
HARD_ASPECTS = {"conjunction", "square", "opposition"}
SOFT_ASPECTS = {"sextile", "trine"}


def bradley_index(
    positions: Dict[str, float],
    orbs: Optional[Dict[str, float]] = None,
    planets: Optional[List[str]] = None,
) -> Dict[str, float]:
    """Compute the classic Bradley index for a given day.

    Checks all planetary pairs against the five major aspect types.
    For each hit, adds the weight from BRADLEY_WEIGHTS to the running total.

    Returns:
      ``{total, hard_sum, soft_sum, aspect_count}``
    """
    if orbs is None:
        orbs = {
            "conjunction": 8.0,
            "sextile": 6.0,
            "square": 6.0,
            "trine": 8.0,
            "opposition": 8.0,
        }
    names = planets or [p for p in PLANETS if p in positions]
    total = 0.0
    hard_sum = 0.0
    soft_sum = 0.0
    aspect_count = 0

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            p1, p2 = names[i], names[j]
            lon1 = positions.get(p1)
            lon2 = positions.get(p2)
            if lon1 is None or lon2 is None:
                continue
            diff = angle_diff(lon1, lon2)
            for aspect_name, target_angle in ASPECT_ANGLES.items():
                if aspect_name == "quincunx":
                    continue  # not in Bradley's original
                orb_val = orbs.get(aspect_name, 8.0)
                if abs(diff - target_angle) <= orb_val:
                    weight = BRADLEY_WEIGHTS[aspect_name]
                    total += weight
                    aspect_count += 1
                    if aspect_name in HARD_ASPECTS:
                        hard_sum += weight
                    else:
                        soft_sum += weight
                    break  # count each pair once

    return {
        "total": round(total, 2),
        "hard_sum": round(hard_sum, 2),
        "soft_sum": round(soft_sum, 2),
        "aspect_count": aspect_count,
    }


def bradley_empirical_index(
    positions: Dict[str, float],
    weights_dict: Dict[str, float],
    orbs: Optional[Dict[str, float]] = None,
    planets: Optional[List[str]] = None,
) -> float:
    """Variant: use empirical (backtested) weights per aspect type.

    `weights_dict` maps aspect_name → weight, typically derived from
    a regression of historical market returns against aspect hits.
    """
    if orbs is None:
        orbs = {
            "conjunction": 8.0,
            "sextile": 6.0,
            "square": 6.0,
            "trine": 8.0,
            "opposition": 8.0,
        }
    names = planets or [p for p in PLANETS if p in positions]
    total = 0.0

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            p1, p2 = names[i], names[j]
            lon1 = positions.get(p1)
            lon2 = positions.get(p2)
            if lon1 is None or lon2 is None:
                continue
            diff = angle_diff(lon1, lon2)
            for aspect_name, target_angle in ASPECT_ANGLES.items():
                if aspect_name == "quincunx":
                    continue
                if diff <= (target_angle + orbs.get(aspect_name, 8.0)) and \
                   diff >= (target_angle - orbs.get(aspect_name, 8.0)):
                    if abs(diff - target_angle) <= orbs.get(aspect_name, 8.0):
                        total += weights_dict.get(aspect_name, 0.0)
                        break
    return round(total, 2)


def bradley_time_series(
    jd_list: List[float],
    sidereal: bool = False,
) -> List[Dict[str, float]]:
    """Compute Bradley index for a list of Julian days.

    Returns a list of dicts that can be directly converted to a DataFrame.
    """
    from .ephemeris import get_longitudes
    results = []
    for jd in jd_list:
        pos = get_longitudes(jd, sidereal=sidereal)
        bi = bradley_index(pos)
        bi["jd"] = jd
        results.append(bi)
    return results


def bradley_interpretation(index_total: float) -> str:
    """Human-readable interpretation of Bradley index magnitude.

    Approximate thresholds from Bradley/Crawford literature.
    """
    if index_total >= 8.0:
        return "VERY BULLISH — strong harmonic alignment, historically large up moves"
    elif index_total >= 4.0:
        return "BULLISH — positive aspect dominance, upward bias"
    elif index_total >= 0.0:
        return "SLIGHTLY BULLISH — mild positive alignment"
    elif index_total >= -4.0:
        return "SLIGHTLY BEARISH — mild stress alignment"
    elif index_total >= -8.0:
        return "BEARISH — hard aspect dominance, downward pressure"
    else:
        return "VERY BEARISH — extreme stress, historically sharp declines"