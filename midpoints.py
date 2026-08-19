"""Hitt midpoint combination engine.

Robert Hitt (*AstroEcon*, Lesson 10):

  "The most powerful kinds of midpoint combinations are ALSO complex aspect
  patterns such as the GRAND TRINE, the YOD and the T-SQUARE."

  "Midpoint combinations happen every day because the Moon moves very fast
  and makes many combinations. Not all of them are significant enough to
  be worth mentioning ... The most important midpoint combination I have
  found to date is the Uranus = Saturn / Pluto."

Hitt's key historical midpoint hits:

  * Uranus = Saturn / Pluto: exact in 1776, 1852, 1929, 1997 — his #1 signal.
  * July 1996: 6 planets focused on Saturn → "the market suffered greatly"
  * July 23 1998: New Moon + Neptune opp = Jupiter/Pluto + Mercury/Venus focus
    → "maximum mania" → sell opportunity, market sank weeks later.

Ebertin's *Combination of Stellar Influences* keywords are included as
commentary on the most important combinations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .ephemeris import angle_diff


def midpoint(lon_a: float, lon_b: float) -> Tuple[float, float]:
    """Return (direct, opposite) midpoints of two bodies.

    The direct midpoint is (lon_a + lon_b) / 2.  The opposite is 180° away.
    """
    mid = ((lon_a + lon_b) / 2.0) % 360.0
    opp = (mid + 180.0) % 360.0
    return mid, opp


def hit_midpoint(lon_target: float, midpoint_point: float, orb: float = 1.0) -> bool:
    """Return True if `lon_target` is within `orb` of `midpoint_point`.

    Also checks the 180° opposite (equivalent hit).
    """
    d = angle_diff(lon_target, midpoint_point)
    return d <= orb


def find_midpoint_hits(
    positions: Dict[str, float],
    planet_pairs: List[Tuple[str, str]],
    target_planet: str,
    orb: float = 1.0,
) -> List[Dict[str, Any]]:
    """Find all hits where `target_planet` is at the midpoint of a pair.

    Returns a list of ``{pair, midpoint_deg, orb}`` entries.
    """
    if target_planet not in positions:
        return []
    lon_target = positions[target_planet]
    results = []
    for p1, p2 in planet_pairs:
        if p1 not in positions or p2 not in positions:
            continue
        mid, opp = midpoint(positions[p1], positions[p2])
        d_mid = angle_diff(lon_target, mid)
        d_opp = angle_diff(lon_target, opp)
        best = min(d_mid, d_opp)
        if best <= orb:
            results.append({
                "pair": (p1, p2),
                "midpoint_deg": round(mid, 3),
                "hit_via_opposite": d_opp < d_mid,
                "orb": round(best, 3),
            })
    results.sort(key=lambda r: r["orb"])
    return results


# ── Known key midpoint combinations from Hitt Lesson 10 ───────────────

# These are the combos Hitt explicitly discusses or implies are important.
# Each entry: (planet_pair, target_planet, ebertin_keywords)
HITT_KEY_MIDPOINTS = [
    (("Saturn", "Pluto"), "Uranus", "innovations breaking existing structures"),
    (("Uranus", "Pluto"), "Mars", "fanaticism, an act of violence, the mania of destruction — Ebertin"),
    (("Uranus", "Pluto"), "Moon", "intuition, restlessness, daring and audaciousness, ambition, determination, bringing about change by force — Ebertin"),
    (("Jupiter", "Neptune"), "Saturn", "creative endurance, materialization of spiritual ideals"),
    (("Jupiter", "Pluto"), "Saturn", "consolidation of power, wealth through authority"),
    (("Saturn", "Uranus"), "Jupiter", "lucky breakthroughs, expansion after restriction"),
    (("Saturn", "Pluto"), "Neptune", "dissolution of rigid structures, hidden transformation"),
    (("Saturn", "Uranus"), "Neptune", "spiritual discipline, idealized innovation"),
    (("Jupiter", "Saturn"), "Uranus", "surprise opportunity, sudden expansion of limits"),
]


def uranus_saturn_pluto(positions: Dict[str, float], orb: float = 1.0) -> Optional[Dict[str, Any]]:
    """Check for Hitt's #1 signal: Uranus at Saturn/Pluto midpoint (or its opposite).

    "The most important midpoint combination I have found to date is the
    Uranus = Saturn / Pluto that was exact in 1776, 1852, 1929, and 1997."
    — Robert Hitt

    The midpoint axis is astrologically symmetric: a hit on the 180° opposite
    of the midpoint (same axis) is also valid.  On Hitt's cited 1997-04-14
    "significant market low", Uranus = 308.3° is opposite the Saturn/Pluto
    midpoint of 128.7° (orb 0.32°) — that is the exact hit.

    Returns ``{pair, midpoint_deg, orb, historical_years, via_opposite}`` or None.
    """
    if "Uranus" not in positions or "Saturn" not in positions or "Pluto" not in positions:
        return None
    mid, opp = midpoint(positions["Saturn"], positions["Pluto"])
    d_mid = angle_diff(positions["Uranus"], mid)
    d_opp = angle_diff(positions["Uranus"], opp)
    best = min(d_mid, d_opp)
    if best <= orb:
        via_opposite = d_opp < d_mid
        hit_deg = opp if via_opposite else mid
        return {
            "pair": ("Saturn", "Pluto"),
            "midpoint_deg": round(hit_deg, 3),
            "orb": round(best, 3),
            "via_opposite": via_opposite,
            "historical_years": [1776, 1852, 1929, 1997],
        }
    return None


def all_key_midpoint_hits(
    positions: Dict[str, float],
    orb: float = 1.0,
) -> List[Dict[str, Any]]:
    """Run all HITT_KEY_MIDPOINTS checks against `positions`.

    Returns a list of ``{pair, target, midpoint_deg, orb, ebertin_keywords}``.
    """
    results = []
    for (p1, p2), target, keywords in HITT_KEY_MIDPOINTS:
        hits = find_midpoint_hits(positions, [(p1, p2)], target, orb=orb)
        for h in hits:
            results.append({
                "pair": (p1, p2),
                "target": target,
                "midpoint_deg": h["midpoint_deg"],
                "orb": h["orb"],
                "ebertin_keywords": keywords,
            })
    return results


def midpoint_scan(
    positions: Dict[str, float],
    orb: float = 1.0,
) -> List[Dict[str, Any]]:
    """Full combinatorial scan: check all 10×9/2 = 45 pairs against all 10 bodies.

    Returns all hits sorted by orb (closest first).  This is the daily midpoint
    overview Hitt would scan for important days.
    """
    from .ephemeris import PLANETS
    bodies = [p for p in PLANETS if p in positions]
    results = []
    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            p1, p2 = bodies[i], bodies[j]
            lon1, lon2 = positions[p1], positions[p2]
            mid, _ = midpoint(lon1, lon2)
            # check every body against this midpoint
            for target in bodies:
                if target in (p1, p2):
                    continue
                d = angle_diff(positions[target], mid)
                if d <= orb:
                    results.append({
                        "pair": (p1, p2),
                        "target": target,
                        "midpoint_deg": round(mid, 3),
                        "orb": round(d, 3),
                    })
    results.sort(key=lambda r: r["orb"])
    return results