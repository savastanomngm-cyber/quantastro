"""Swiss Ephemeris wrapper.

All coordinates are tropical geocentric ecliptic longitudes in degrees
(0..360).  Sidereal support is provided because Robert Hitt explicitly
mentions using sidereal and heliocentric reference frames as well.

The ten bodies tracked are the classical seven (Sun, Moon, Mercury, Venus,
Mars, Jupiter, Saturn) plus Uranus, Neptune, Pluto — together with the
True North Node, which Henry Weingarten references repeatedly (nodes).

Planetary speed is used to detect retrograde motion (negative geocentric
longitude speed = apparent retrograde), which both authors treat as an
intermediate-term reversal candidate.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import swisseph as swe

# The 10 classical + modern bodies used throughout the engine.
PLANETS: List[str] = [
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
]

# swisseph body constants.  Node handled separately.
PLANET_TO_SWE: Dict[str, int] = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}

SIGNS: List[str] = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


def jd_from_date(year: int, month: int, day: int, hour: float = 0.0) -> float:
    """Julian day (UT) from calendar date. `hour` is a decimal UT hour."""
    return swe.julday(year, month, day, hour)


def _calc(jd: float, body: int, sidereal: bool) -> Tuple[float, float]:
    """Return (longitude_deg, speed_deg_per_day) for a body at a Julian day."""
    flags = swe.FLG_SPEED
    if sidereal:
        flags |= swe.FLG_SIDEREAL
    pos, ret = swe.calc_ut(jd, body, flags)
    # pos[0] = longitude, ret = speed (negative => retrograde)
    return float(pos[0]), float(ret)


def get_longitudes(jd: float, sidereal: bool = False) -> Dict[str, float]:
    """Geocentric ecliptic longitudes (degrees) for all bodies at `jd`.

    Includes the True North Node under key ``"Node"``.
    """
    out: Dict[str, float] = {}
    for name, body in PLANET_TO_SWE.items():
        lon, _ = _calc(jd, body, sidereal)
        out[name] = lon % 360.0
    # True node
    lon_node, _ = _calc(jd, swe.TRUE_NODE, sidereal)
    out["Node"] = lon_node % 360.0
    return out


def get_speeds(jd: float, sidereal: bool = False) -> Dict[str, float]:
    """Geocentric longitude speeds (deg/day). Negative => retrograde."""
    out: Dict[str, float] = {}
    for name, body in PLANET_TO_SWE.items():
        _, spd = _calc(jd, body, sidereal)
        out[name] = spd
    _, spd_node = _calc(jd, swe.TRUE_NODE, sidereal)
    out["Node"] = spd_node
    return out


def get_sign(lon: float) -> Tuple[str, int, float]:
    """Return (sign_name, sign_index_0_11, degrees_within_sign) for a longitude."""
    lon = lon % 360.0
    idx = int(lon // 30) % 12
    return SIGNS[idx], idx, lon % 30.0


def angle_diff(a: float, b: float) -> float:
    """Shortest angular separation in degrees, always in [0, 180]."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


def get_moon_phase(jd: float) -> Dict[str, float]:
    """Moon phase measured as Sun->Moon elongation.

    Returns a dict with:
      - ``elongation``:   sun-to-moon angle in degrees (0..360)
      - ``phase_angle``:  alias of elongation
      - ``illumination``: 0..1 fraction lit
      - ``age``:          days since last new moon (approximate)
    """
    lon = get_longitudes(jd)
    sun_lon = lon["Sun"]
    moon_lon = lon["Moon"]
    elongation = (moon_lon - sun_lon) % 360.0
    illumination = (1.0 - __import__("math").cos(__import__("math").radians(elongation))) / 2.0
    age = elongation / 360.0 * 29.53058867
    return {
        "elongation": elongation,
        "phase_angle": elongation,
        "illumination": illumination,
        "age": age,
    }
