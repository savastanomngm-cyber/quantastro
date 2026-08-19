"""Hitt aspect taxonomy and complex pattern detection.

Robert Hitt (*AstroEcon*, Lessons 5 & 7):

  * **Hard aspects** (0°, 90°, 180°, 270° = conjunction, squares, opposition)
    are trend-change candidates: "the market seems to want to change trends on
    hard aspects and rarely does so on trines."

  * **Soft aspects** (60° sextile, 120° trine) are continuation / inertia:
    "Trines are a continuation and not a turning point indication."

  * **Complex patterns** (Lesson 7) are rare multi-planet geometries whose
    effects can last months or years.  Hitt provides dated historical instances
    for each pattern, which are encoded here as ``KNOWN_*`` test vectors.

All functions take a ``positions`` dict (planet name → longitude in degrees)
such as the one produced by ``ephemeris.get_longitudes(...)``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .ephemeris import angle_diff

# ── Default orbs (in degrees) ──────────────────────────────────────────
DEFAULT_ORBS = {
    "conjunction": 8.0,
    "opposition": 6.0,
    "square": 6.0,
    "sextile": 4.0,
    "trine": 8.0,
    "quincunx": 3.0,  # 150° — used only for Yod detection (Hitt: tight orb)
}

# ── Aspect classification ─────────────────────────────────────────────

ASPECT_ANGLES: Dict[str, float] = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "quincunx": 150.0,
    "opposition": 180.0,
}


def classify_aspect(
    angle: float, orbs: Optional[Dict[str, float]] = None
) -> Optional[str]:
    """Return the aspect type if `angle` (shortest arc) falls within orb, else None.

    ``angle`` should already be the shortest arc (0..180°).
    """
    orbs = orbs or DEFAULT_ORBS
    for name, target in sorted(ASPECT_ANGLES.items(), key=lambda x: x[0] != "conjunction"):
        if abs(angle - target) <= orbs.get(name, DEFAULT_ORBS[name]):
            return name
    return None


def find_all_aspects(
    positions: Dict[str, float],
    orbs: Optional[Dict[str, float]] = None,
    planets: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Return all planetary aspects within orb, sorted closest-first.

    Each entry: ``{p1, p2, type, angle, orb}``.

    Deduplication: each pair appears only once (p1 < p2 lexicographically).
    """
    orbs = orbs or DEFAULT_ORBS
    names = planets or sorted(positions.keys())
    results: List[Dict[str, Any]] = []
    for i, p1 in enumerate(names):
        for p2 in names[i + 1:]:
            if p1 not in positions or p2 not in positions:
                continue
            angle = angle_diff(positions[p1], positions[p2])
            aspect = classify_aspect(angle, orbs)
            if aspect:
                target_angle = ASPECT_ANGLES[aspect]
                results.append({
                    "p1": p1,
                    "p2": p2,
                    "type": aspect,
                    "angle": round(angle, 3),
                    "orb": round(abs(angle - target_angle), 3),
                })
    results.sort(key=lambda r: r["orb"])
    return results


# ── Complex pattern detection (Hitt Lesson 7) ─────────────────────────

# Historical instances from Hitt's text — for validation.
# Stellium 1987-08-24: Sun, Moon, Mercury, Venus, Mars within 4°
# Stellium 1994-01-11: Sun, Moon, Mercury, Venus, Mars, Uranus, Neptune within 8°
# Stellium 2000-05-04: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn within 26° (Taurus)
# Grand Cross 1999-08-11: solar eclipse opp Uranus, squared Mars+Saturn
# T-Square 1931-07-15: Saturn opp Pluto, both squared Uranus → depression low
# T-Square 2000-10-04: Jupiter opp Pluto, Mars squares both → Israel violence
# Grand Trine 1997-07-24
# Yod 1997-11-17: Mars = Uranus/Pluto apex, Moon opp Mars

KNOWN_STELLIUM_DATES = [
    "1987-08-24",
    "1994-01-11",
    "2000-05-04",
]
KNOWN_GRAND_CROSS_DATE = "1999-08-11"
KNOWN_T_SQUARE_DATES = ["1931-07-15", "2000-10-04"]
KNOWN_GRAND_TRINE_DATE = "1997-07-24"
KNOWN_YOD_DATE = "1997-11-17"


def _find_conjunction_clusters(
    positions: Dict[str, float],
    max_orb: float = 8.0,
    planets: Optional[List[str]] = None,
) -> List[List[str]]:
    """Return groups of planets that are all mutually conjunct (within max_orb).

    Uses single-linkage clustering across longitude differences.
    """
    names = planets or [p for p in positions if p != "Node"]
    if not names:
        return []
    # sort by longitude
    sorted_bodies = sorted(
        [(n, positions[n]) for n in names if n in positions],
        key=lambda x: x[1],
    )
    n = len(sorted_bodies)
    if n < 2:
        return []

    # Adjacency matrix — distance in shortest arc
    clusters: List[List[str]] = []
    current = [sorted_bodies[0][0]]
    current_lons = [sorted_bodies[0][1]]
    for i in range(1, n):
        name_i, lon_i = sorted_bodies[i]
        # is this body within max_orb of the CLUSTER (actually the last body)
        _, lon_last = sorted_bodies[i - 1]
        if angle_diff(lon_i, lon_last) <= max_orb:
            current.append(name_i)
            current_lons.append(lon_i)
        else:
            if len(current) >= 2:
                clusters.append(current)
            current = [name_i]
            current_lons = [lon_i]
    if len(current) >= 2:
        clusters.append(current)

    # Also wrap-around check (last and first)
    if n >= 2:
        first_name, first_lon = sorted_bodies[0]
        last_name, last_lon = sorted_bodies[-1]
        # check if they should be merged across 360° boundary
        wrap_dist = angle_diff(last_lon, first_lon + 360.0) if last_lon > first_lon else angle_diff(last_lon, first_lon)
        # If the first and last clusters both exist and cross the boundary
        if clusters:
            first_cluster = clusters[0]
            last_cluster = clusters[-1]
            if first_cluster is not last_cluster:
                # Check if bodies at ends are close across 0°/360°
                if angle_diff(sorted_bodies[-1][1], sorted_bodies[0][1] + 360.0) <= max_orb:
                    merged = last_cluster + first_cluster
                    clusters = [merged] + clusters[1:-1]

    return [c for c in clusters if len(c) >= 2]


def find_stellium(
    positions: Dict[str, float],
    min_bodies: int = 4,
    max_orb: float = 8.0,
    planets: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Detect a Stellium: `min_bodies`+ planets conjunct within `max_orb`.

    Hitt Lesson 7: "A STELLIUM is when 4 or more planets are conjunct
    within a few degrees."  Historical instances use orbs of 4° to 26°,
    so `max_orb` is configurable.

    Returns ``{bodies, max_orb_among_cluster, sign, degree_range}`` or None.
    """
    clusters = _find_conjunction_clusters(positions, max_orb, planets)
    for cluster in clusters:
        if len(cluster) >= min_bodies:
            lons = [positions[p] for p in cluster]
            lon_min = min(lons, key=lambda x: x % 360.0) % 360.0
            lon_max = max(lons, key=lambda x: x % 360.0) % 360.0
            # handle wrap
            if lon_max < lon_min:
                lon_max += 360.0
            deg_range = lon_max - lon_min
            from .ephemeris import get_sign
            mid_lon = (lon_min + deg_range / 2.0) % 360.0
            sign_name, _, _ = get_sign(mid_lon)
            return {
                "bodies": cluster,
                "bodies_count": len(cluster),
                "max_orb": round(deg_range, 2),
                "sign": sign_name,
                "degree_range": round(deg_range, 2),
            }
    return None


def find_grand_cross(
    positions: Dict[str, float],
    square_orb: float = 6.0,
    opp_orb: float = 6.0,
    planets: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Detect a Grand Cross: 2 oppositions at ~90° to each other => 4 squares.

    Hitt: "2 oppositions and 4 squares — quite chaotic and difficult to control."
    His example: 1999-08-11 solar eclipse opp Uranus, squared by Mars+Saturn.
    """
    names = planets or [p for p in positions if p != "Node"]
    n = len(names)
    for a in range(n):
        for b in range(a + 1, n):
            p_a, p_b = names[a], names[b]
            lon_a, lon_b = positions.get(p_a), positions.get(p_b)
            if lon_a is None or lon_b is None:
                continue
            d_ab = angle_diff(lon_a, lon_b)
            if abs(d_ab - 180) > opp_orb:
                continue
            # p_a and p_b are in opposition — now find a second opposition
            for c in range(n):
                if c in (a, b):
                    continue
                for d in range(c + 1, n):
                    if d in (a, b):
                        continue
                    p_c, p_d = names[c], names[d]
                    lon_c, lon_d = positions.get(p_c), positions.get(p_d)
                    if lon_c is None or lon_d is None:
                        continue
                    d_cd = angle_diff(lon_c, lon_d)
                    if abs(d_cd - 180) > opp_orb:
                        continue
                    # Check that the two opposition axes are ~90° apart
                    axis1_angle = (lon_a + 90.0) % 360.0  # square to first opp
                    d_ax = angle_diff(lon_c, axis1_angle)
                    if d_ax <= square_orb or angle_diff(lon_c + 180.0, axis1_angle % 360.0) <= square_orb:
                        return {
                            "opposition_1": (p_a, p_b),
                            "opposition_2": (p_c, p_d),
                            "bodies": [p_a, p_b, p_c, p_d],
                            "cross_angle": round(d_ax, 2),
                        }
    return None


def find_t_square(
    positions: Dict[str, float],
    square_orb: float = 6.0,
    opp_orb: float = 6.0,
    planets: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Detect a T-Square: 3 planets — opposition + 2 squares.

    Hitt: 1931-07-15 Saturn opp Pluto, both squared by Uranus (depression low);
    2000-10-04 Jupiter opp Pluto, Mars squares both (Israel violence).
    """
    names = planets or [p for p in positions if p != "Node"]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            p_a, p_b = names[i], names[j]
            lon_a, lon_b = positions.get(p_a), positions.get(p_b)
            if lon_a is None or lon_b is None:
                continue
            if abs(angle_diff(lon_a, lon_b) - 180.0) > opp_orb:
                continue
            # opposition found — look for a 3rd body squaring both
            for k in range(len(names)):
                if k in (i, j):
                    continue
                p_c = names[k]
                lon_c = positions.get(p_c)
                if lon_c is None:
                    continue
                d_ac = angle_diff(lon_a, lon_c)
                d_bc = angle_diff(lon_b, lon_c)
                if abs(d_ac - 90.0) <= square_orb and abs(d_bc - 90.0) <= square_orb:
                    # Lone — which one is the apex vs base?
                    # In T-Square, the squaring body is the apex.
                    return {
                        "opposition": (p_a, p_b),
                        "apex": p_c,
                        "bodies": [p_a, p_b, p_c],
                        "orb_sq_1": round(abs(d_ac - 90.0), 2),
                        "orb_sq_2": round(abs(d_bc - 90.0), 2),
                    }
    return None


def find_grand_trine(
    positions: Dict[str, float],
    trine_orb: float = 8.0,
    planets: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Detect a Grand Trine: 3 planets each ~120° apart (equilateral triangle).

    Hitt: "Grand trines are trend continuation and rarely seen on trend
    changes."  His example: 1997-07-24.
    """
    names = planets or [p for p in positions if p != "Node"]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            for k in range(j + 1, len(names)):
                p1, p2, p3 = names[i], names[j], names[k]
                lon1, lon2, lon3 = positions.get(p1), positions.get(p2), positions.get(p3)
                if lon1 is None or lon2 is None or lon3 is None:
                    continue
                d12 = angle_diff(lon1, lon2)
                d23 = angle_diff(lon2, lon3)
                d31 = angle_diff(lon3, lon1)
                if (abs(d12 - 120.0) <= trine_orb and
                    abs(d23 - 120.0) <= trine_orb and
                    abs(d31 - 120.0) <= trine_orb):
                    return {
                        "bodies": [p1, p2, p3],
                        "orbs": [round(abs(d12 - 120), 2), round(abs(d23 - 120), 2), round(abs(d31 - 120), 2)],
                    }
    return None


def find_yod(
    positions: Dict[str, float],
    sextile_orb: float = 4.0,
    quincunx_orb: float = 3.0,
    planets: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Detect a Yod (Finger of God): 2 planets sextile, both quincunx a 3rd (apex).

    Hitt Lesson 7: "NOT a minor aspect pattern ... the Yod brings a very
    violent aspect pattern ... the planet at the apex is the FOCUS of energy."
    His example: 1997-11-17 Mars = Uranus/Pluto apex (sextile Uranus-Pluto).

    Hitt uses a TIGHT orb for the quincunx — the apex must be precisely at
    the midpoint.  We use configurable defaults: sextile 4°, quincunx 3°.
    """
    names = planets or [p for p in positions if p != "Node"]
    # First find sextile pairs
    sextile_pairs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            p1, p2 = names[i], names[j]
            lon1, lon2 = positions.get(p1), positions.get(p2)
            if lon1 is None or lon2 is None:
                continue
            if abs(angle_diff(lon1, lon2) - 60.0) <= sextile_orb:
                sextile_pairs.append((p1, p2, lon1, lon2))

    # For each sextile pair, check if any 3rd body is quincunx BOTH
    for p1, p2, lon1, lon2 in sextile_pairs:
        for k in range(len(names)):
            apex = names[k]
            if apex in (p1, p2):
                continue
            lon_apex = positions.get(apex)
            if lon_apex is None:
                continue
            d1 = angle_diff(lon1, lon_apex)
            d2 = angle_diff(lon2, lon_apex)
            if abs(d1 - 150.0) <= quincunx_orb and abs(d2 - 150.0) <= quincunx_orb:
                return {
                    "sextile": (p1, p2),
                    "apex": apex,
                    "bodies": [p1, p2, apex],
                    "orb_q1": round(abs(d1 - 150.0), 2),
                    "orb_q2": round(abs(d2 - 150.0), 2),
                }
    return None


def detect_all_complex_patterns(
    positions: Dict[str, float],
    orbs: Optional[Dict[str, float]] = None,
    planets: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run all complex pattern detectors and return a summary dict.

    Keys present when a pattern is found: ``stellium``, ``grand_cross``,
    ``t_square``, ``grand_trine``, ``yod``.  None when absent.
    """
    orbs = orbs or DEFAULT_ORBS
    names = planets or list(positions.keys())
    return {
        "stellium": find_stellium(positions, max_orb=orbs.get("conjunction", 8.0), planets=names),
        "grand_cross": find_grand_cross(positions, square_orb=orbs.get("square", 6.0), opp_orb=orbs.get("opposition", 6.0), planets=names),
        "t_square": find_t_square(positions, square_orb=orbs.get("square", 6.0), opp_orb=orbs.get("opposition", 6.0), planets=names),
        "grand_trine": find_grand_trine(positions, trine_orb=orbs.get("trine", 8.0), planets=names),
        "yod": find_yod(positions, sextile_orb=orbs.get("sextile", 4.0), quincunx_orb=orbs.get("quincunx", 3.0), planets=names),
    }