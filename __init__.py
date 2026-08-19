"""astroquant — quantitative astro-trading signal engine.

A deterministic implementation of the rule-based techniques described in:

* Robert Hitt, *AstroEcon: Financial Astrology and Technical Analysis* (1997–2000)
  — aspect taxonomy, complex aspect patterns (Stellium / Grand Cross /
  T-Square / Grand Trine / Yod), midpoint combinations, intraday
  angle-crossing triggers.

* Henry Weingarten, *Investing by the Stars* (2nd ed., 2000)
  — planetary rulerships, Jupiter–Saturn harmonic cycles, retrogrades,
  lunar phases, cross-confirmation ("rule of three").

* Donald Bradley / Arch Crawford / W. D. Gann lineage
  — the weighted daily aspect sum ("Bradley sidereal potential line").

The engine is *pure arithmetic on planetary longitudes and angles*: there is
no interpretation step. Every signal reduces to a computable number so it can
be event-studied and backtested against market data.
"""

from .ephemeris import (
    PLANETS,
    get_longitudes,
    get_speeds,
    get_sign,
    get_moon_phase,
    jd_from_date,
    angle_diff,
)

__version__ = "0.1.0"
__all__ = [
    "PLANETS",
    "get_longitudes",
    "get_speeds",
    "get_sign",
    "get_moon_phase",
    "jd_from_date",
    "angle_diff",
]
