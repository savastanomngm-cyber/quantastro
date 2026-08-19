"""Intraday angle-crossing engine.

Robert Hitt (*AstroEcon*, Lesson 10 & Intraday Signals example):

  "These times do NOT represent aspects between planets which occur at the
  same time at all places on earth. These times are SPECIFIC to the
  [exchange] location ... dealing with the passage of the planets over the
  4 cardinal points on the earth at a specific location during the 24 hour
  day AS THE EARTH ROTATES."

Hitt's documented method (from his Vega Astro Clock setup):
  - only list transits-to-transits for the 4 major angles (Asc, MC, Dsc, Nadir)
  - orb: 0° 15' (0.25°) for transit-to-transit
  - Chicago is the reference location for S&P futures

The "day character" concept: the snapshot at market open determines the
theme for the day.  If a planet is exactly on an angle at the open, it is
the featured influence throughout the day.

Refactored from the original astrosignaltest.py Section 3.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import swisseph as swe


# ── Exchange presets ─────────────────────────────────────────────────
@dataclass
class Exchange:
    """Trading venue with location + timezone offset from UTC (hours)."""
    name: str
    lat: float
    lon: float
    utc_offset: float  # hours; negative = west of Greenwich
    trading_start: float  # local hour
    trading_end: float  # local hour

EXCHANGES = {
    "CHICAGO": Exchange("Chicago (CME)", 41.8781, -87.6298, -6.0, 8.30, 15.15),
    "NYC": Exchange("New York (NYSE)", 40.7128, -74.0060, -5.0, 9.5, 16.0),
    "LONDON": Exchange("London (LSE)", 51.5074, -0.1278, 0.0, 8.0, 16.5),
    "TOKYO": Exchange("Tokyo (TSE)", 35.6762, 139.6503, 9.0, 9.0, 15.0),
}

PLANETS_FOR_ANGLES = ["Sun", "Moon", "Mercury", "Venus", "Mars",
                       "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]


def _planet_body(name: str) -> int:
    """Map planet name to swisseph body constant."""
    mapping = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
        "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
        "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE,
        "Pluto": swe.PLUTO,
    }
    return mapping[name]


def _alt_az(jd: float, lat: float, lon: float, body: int) -> Tuple[float, float]:
    """Apparent altitude and azimuth (degrees) of a body at a location.

    Returns (true_altitude, azimuth).  Azimuth is measured from SOUTH,
    going WEST (0=South, 90=West, 180=North, 270=East) — swisseph convention.
    """
    # Compute equatorial position directly (RA, declination, distance)
    pos_eq, ret = swe.calc_ut(jd, body, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)
    geo_pos = (lon, lat, 0.0)  # (longitude, latitude, altitude)
    azalt = swe.azalt(jd, swe.EQU2HOR, geo_pos, 0.0, 15.0, pos_eq[:3])
    # azalt = (azimuth, true_altitude, apparent_altitude); azimuth from South->West
    return float(azalt[1]), float(azalt[0])  # true altitude, azimuth


def _crossing(
    alt_before: float, alt_after: float,
    az_before: float, az_after: float,
) -> Tuple[bool, bool, bool, bool]:
    """Check if a body crossed Asc, MC, Dsc, or Nadir between two samples.

    swisseph azimuth is measured from the SOUTH point going WEST:
      0° = South (Midheaven / upper culmination)
      90° = West (Descendant)
      180° = North (Nadir / lower culmination)
      270° = East (Ascendant)

    Crossing detection (assume small step so azimuth wraps are monotonic):
      - Ascendant: body crosses EAST point. In south-based azimuth this is 270°.
        But simpler and robust: altitude crosses 0 going UP = rising.
      - Descendant: altitude crosses 0 going DOWN = setting.
      - MC: body crosses azimuth 0° (South) via upper culmination.
      - Nadir: body crosses azimuth 180° (North) via lower culmination.
    """
    asc = alt_before < 0 and alt_after >= 0
    dsc = alt_before > 0 and alt_after <= 0

    # Azimuth wrap handling for MC (0°) and Nadir (180°)
    # MC: azimuth moves through 0° (South). Detect 359→0→1 wrap.
    mc = False
    ndr = False
    # Unwrap the two azimuths to a continuous range around az_before
    az_b = az_before % 360.0
    az_a = az_after % 360.0
    delta = (az_a - az_b + 180.0) % 360.0 - 180.0  # shortest signed diff
    az_a_unwrapped = az_b + delta

    # MC crossing = pass through 0° downward in signed terms (from >0 to <0),
    # i.e. azimuth decreasing through 0. But it could also be <360→>0 wrap.
    # Detect: az_b in (0,180) means approaching 0, az_a_unwrapped <= 0 → crossed South.
    if az_b < 180.0 and az_a_unwrapped <= 0.0:
        mc = True
    elif az_b >= 180.0 and az_a_unwrapped >= 360.0:
        # crossed 360 = 0 = South from the other side
        mc = True
    # Nadir = North = 180°. 
    if az_b < 180.0 and az_a_unwrapped >= 180.0:
        ndr = True
    elif az_b >= 180.0 and az_a_unwrapped <= 180.0:
        ndr = True

    return asc, mc, dsc, ndr


def find_angle_crossings(
    jd: float,
    lat: float,
    lon: float,
    step_minutes: int = 5,
    planets: Optional[List[str]] = None,
    start_hour: Optional[float] = None,
    end_hour: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Find all planetary angle-crossings for a given day and location.

    Args:
        jd: Julian day (UT)
        lat, lon: observer location
        step_minutes: time resolution
        planets: which bodies to track (default: all 10)
        start_hour, end_hour: UT hours to scan (default: full day 0-24)

    Returns:
        List of ``{time_ut, time_str, planet, angle, significance}``
    """
    names = planets or PLANETS_FOR_ANGLES
    bodies = {name: _planet_body(name) for name in names}
    start_min = int((start_hour or 0) * 60)
    end_min = int((end_hour or 24) * 60)

    # Compute base Julian day at UT midnight
    jd_midnight = math.floor(jd - 0.5) + 0.5

    results = []
    for m in range(start_min, end_min, step_minutes):
        t_before = jd_midnight + m / 1440.0
        t_after = jd_midnight + (m + step_minutes) / 1440.0

        dt = datetime.utcfromtimestamp(
            (jd_midnight - 2440587.5) * 86400 + m * 60
        )

        for name, body in bodies.items():
            alt_b, az_b = _alt_az(t_before, lat, lon, body)
            alt_a, az_a = _alt_az(t_after, lat, lon, body)
            asc, mc, dsc, ndr = _crossing(alt_b, alt_a, az_b, az_a)

            time_str = dt.strftime("%H:%M")
            if asc:
                results.append({
                    "time_ut": time_str, "planet": name,
                    "angle": "ASC", "significance": "Rising — new energy emerges, turning point",
                })
            if dsc:
                results.append({
                    "time_ut": time_str, "planet": name,
                    "angle": "DSC", "significance": "Setting — culmination, release of energy",
                })
            if mc:
                results.append({
                    "time_ut": time_str, "planet": name,
                    "angle": "MC", "significance": "Noon culmination — peak visibility, maximum influence",
                })
            if ndr:
                results.append({
                    "time_ut": time_str, "planet": name,
                    "angle": "NDR", "significance": "Nadir — hidden depths, bottom of cycle",
                })

    results.sort(key=lambda r: r["time_ut"])
    return results


def day_character(
    jd: float, lat: float, lon: float, trading_start_ut: float,
) -> Dict[str, Any]:
    """Hitt's "day character": snapshot of the angles at market open.

    Planets on angles at the open → featured throughout the day.
    Complex patterns in focus → dominant theme.

    Returns:
      ``{planets_on_angles, asc_degree, mc_degree, dominant_planet}``
    """
    # Compute houses for the market open
    houses, ascmc = swe.houses(jd, lat, lon, b'P')  # Placidus
    asc_deg = ascmc[0]
    mc_deg = ascmc[1]
    dsc_deg = (asc_deg + 180) % 360
    ndr_deg = (mc_deg + 180) % 360

    from .ephemeris import get_longitudes, angle_diff, get_sign
    positions = get_longitudes(jd)

    planets_on_angles = []
    for name in PLANETS_FOR_ANGLES:
        lon_body = positions.get(name)
        if lon_body is None:
            continue
        for angle_name, angle_lon in [("ASC", asc_deg), ("MC", mc_deg),
                                       ("DSC", dsc_deg), ("NDR", ndr_deg)]:
            if angle_diff(lon_body, angle_lon) <= 2.0:
                sign_name, _, deg_in_sign = get_sign(lon_body)
                planets_on_angles.append({
                    "planet": name,
                    "angle": angle_name,
                    "orb": round(angle_diff(lon_body, angle_lon), 2),
                    "sign": sign_name,
                    "deg_in_sign": round(deg_in_sign, 1),
                })

    asc_sign, _, _ = get_sign(asc_deg)
    mc_sign, _, _ = get_sign(mc_deg)

    # Dominant planet = one closest to any angle
    dominant = None
    if planets_on_angles:
        planets_on_angles.sort(key=lambda x: x["orb"])
        dominant = planets_on_angles[0]["planet"]

    return {
        "asc_degree": round(asc_deg, 3),
        "asc_sign": asc_sign,
        "mc_degree": round(mc_deg, 3),
        "mc_sign": mc_sign,
        "planets_on_angles": planets_on_angles,
        "dominant_planet": dominant,
    }


def get_local_hour(ut_hour: float, utc_offset: float) -> float:
    """Convert decimal UT hour to local decimal hour."""
    return (ut_hour + utc_offset) % 24.0


def trading_crossings(
    jd: float,
    exchange_name: str,
    step_minutes: int = 5,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Full intraday report for an exchange: crossings during trading hours + day character.

    Returns (crossings_list, day_character_dict).
    """
    exc = EXCHANGES[exchange_name.upper()]
    jd_noon = math.floor(jd - 0.5) + 0.5 + 0.5  # approximate noon UT

    # Convert trading start/end from local to UT
    start_ut = exc.trading_start - exc.utc_offset
    end_ut = exc.trading_end - exc.utc_offset
    if start_ut < 0:
        start_ut += 24.0
    if end_ut < 0:
        end_ut += 24.0

    crossings = find_angle_crossings(
        jd_noon, exc.lat, exc.lon,
        step_minutes=step_minutes,
        start_hour=start_ut,
        end_hour=end_ut,
    )

    # Convert UTC times to local for display
    for c in crossings:
        ut_h = int(c["time_ut"].split(":")[0]) + int(c["time_ut"].split(":")[1]) / 60.0
        local_h = get_local_hour(ut_h, exc.utc_offset)
        h = int(local_h)
        m = int((local_h - h) * 60)
        c["time_local"] = f"{h:02d}:{m:02d}"
        c["exchange"] = exc.name

    # Day character at market open
    jd_open = jd_noon + (start_ut - 12.0) / 24.0
    dc = day_character(jd_open, exc.lat, exc.lon, start_ut)

    return crossings, dc