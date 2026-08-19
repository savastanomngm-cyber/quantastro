# astroquant

Deterministic rule-based astro-trading signal engine, implementing the
techniques from:

- **Robert Hitt**, *AstroEcon: Financial Astrology and Technical Analysis*
  (aspect taxonomy, complex patterns, midpoints, intraday angle crossings)
- **Henry Weingarten**, *Investing by the Stars* (rulerships, cycles, retrogrades)
- **Donald Bradley / Arch Crawford** (weighted daily aspect sum)

## Install

```bash
cd /home/user/workspace/astroquant
pip install -e .
```

## Usage

```bash
# Full markdown report for a date
python -m astroquant.run 2026-08-19

# Specify exchange (CHICAGO, NYC, LONDON, TOKYO)
python -m astroquant.run 1987-10-19 --exchange NYC

# Raw JSON output
python -m astroquant.run 1929-10-24 --json
```

## Modules

| Module        | Purpose                                                       |
|---------------|---------------------------------------------------------------|
| `ephemeris`   | Swiss Ephemeris wrapper (longitudes, speeds, signs, phases)   |
| `aspects`     | Hitt aspect taxonomy + complex patterns (Stellium, Grand Cross, T-Square, Grand Trine, Yod) |
| `midpoints`   | Hitt midpoint engine (Uranus=Saturn/Pluto, etc.)              |
| `bradley`     | Bradley/Crawford weighted daily aspect sum                     |
| `intraday`    | Angle-crossing (Asc/MC/Dsc/Nadir) detection                    |
| `run`         | CLI report generator                                           |
| `backtest`    | Event-study and signal-analysis harness                        |

## Key signals

- **Uranus = Saturn/Pluto midpoint** — Hitt's #1 long-term signal (1776, 1852, 1929, 1997)
- **Hard vs soft aspect dominance** — trend-change vs continuation
- **Stellium / Grand Cross / T-Square / Yod** — rare multi-planet geometry
- **Bradley index** — single daily scalar of weighted aspect sum
- **Intraday angle crossings** — precise intraday turn timings for an exchange

## Testing

```bash
python -m pytest astroquant/tests/ -v
```

## Notes

Every signal reduces to pure arithmetic on planetary longitudes/angles — no
AI interpretation. This makes the entire library event-studyable and
backtestable against any price series.
