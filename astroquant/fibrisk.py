r"""Golden-ratio fib envelope anchored on morning range.

Theory
------
The extension constant :math:`\gamma = \sqrt{\phi} \cdot 2\phi/3`,
numerically **1.372**, derives from the product of the circle (:math:`\pi`)
and the golden ratio (:math:`\phi`):

.. math::

   \pi\phi = 5.0832, \qquad
   \gamma = \sqrt{\phi} \cdot \frac{\pi\phi}{3\pi/2}
          = \sqrt{\phi} \cdot \frac{2\phi}{3}
          = 1.372

Price has been observed to exhaust within :math:`\pm\gamma` extensions
of the morning range (or session range).  The levels inside this envelope
form a complete retracement / extension grid that respects both the
linear Fibonacci sequence and the circular :math:`\pi`-cycle — the bridge
between *linear price* and *cyclical time* (the domain of astrology).

Levels
------
+1.372   upper exhaustion bound — fade short when astro confirms
+1.272   :math:`\sqrt{\phi}` standard extension
+1.000   range high
+0.729   1 / 1.372 — custom retracement
+0.618   golden ratio retracement
+0.508   :math:`\pi\phi/10` harmonic constant
 0.000   range anchor (open or session low, direction-dependent)
-0.508   harmonic below anchor
-0.618   golden below anchor
-0.729   custom retracement below
-1.000   range low
-1.272   lower standard extension
-1.372   lower exhaustion bound — fade long when astro confirms
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# ── constants ──────────────────────────────────────────────────────────

PHI = (1.0 + math.sqrt(5.0)) / 2.0          # 1.618034
GAMMA = math.sqrt(PHI) * 2.0 * PHI / 3.0    # 1.372122
GAMMA_INV = 1.0 / GAMMA                     # 0.7289
HARMONIC = PHI * math.pi / 10.0             # 0.5083


# ── envelope ───────────────────────────────────────────────────────────

@dataclass
class FibEnvelope:
    """Price levels for one session, anchored on morning range."""

    anchor: float        # 0-level price (open or session low)
    range_high: float    # +1 level
    range_low: float     # -1 level
    direction: str       # 'long' or 'short' — which side the range extends

    @property
    def range_size(self) -> float:
        return self.range_high - self.range_low

    def levels(self) -> Dict[str, float]:
        """All envelope levels as {name: price}.

        Levels < 1.0 are retracements measured upward from the range LOW.
        Levels > 1.0 are extensions measured upward from the range HIGH.
        Symmetric downward levels are measured from the range HIGH downward
        (retracements < -1.0 are extensions downward).

        This ensures the fib grid is anchored on the actual price range,
        not a mathematical midpoint.
        """
        R = self.range_size
        base_low = self.range_low
        base_high = self.range_high
        lvls: Dict[str, float] = {}

        # ── upward extensions (from high) ──
        lvls["+1.372"] = base_high + R * (GAMMA - 1.0)
        lvls["+1.272"] = base_high + R * (math.sqrt(PHI) - 1.0)
        lvls["+1.000"] = base_high

        # ── upward retracements (from low toward high) ──
        lvls["+0.729"] = base_low + R * GAMMA_INV
        lvls["+0.618"] = base_low + R * (PHI - 1.0)
        lvls["+0.508"] = base_low + R * HARMONIC
        lvls["+0.382"] = base_low + R * 0.382
        lvls["+0.236"] = base_low + R * 0.236

        # ── anchor ──
        # Anchor is the swing origin: for a long setup it's the low;
        # for a short setup it's the high.  Default to midpoint.
        midpoint = (base_low + base_high) / 2.0
        lvls["0.000"] = midpoint

        # ── downward retracements (from high toward low) ──
        lvls["-0.236"] = base_high - R * 0.236
        lvls["-0.382"] = base_high - R * 0.382
        lvls["-0.508"] = base_high - R * HARMONIC
        lvls["-0.618"] = base_high - R * (PHI - 1.0)
        lvls["-0.729"] = base_high - R * GAMMA_INV

        # ── downward extensions (from low) ──
        lvls["-1.000"] = base_low
        lvls["-1.272"] = base_low - R * (math.sqrt(PHI) - 1.0)
        lvls["-1.372"] = base_low - R * (GAMMA - 1.0)

        return lvls

    def nearest_level(self, price: float) -> Tuple[str, float, float]:
        """Find the closest envelope level to `price`.

        Returns (level_name, level_price, distance_in_pct_of_range).
        """
        lvls = self.levels()
        best_name, best_price = None, None
        best_dist = float("inf")
        for name, lvl in lvls.items():
            dist = abs(price - lvl)
            if dist < best_dist:
                best_dist = dist
                best_name, best_price = name, lvl
        return best_name, best_price, (best_dist / self.range_size * 100.0)

    def is_at_extreme(self, price: float, pct: float = 2.0) -> Optional[str]:
        """Return '+1.372' or '-1.372' if price is within `pct`% of range."""
        name, lvl, dist_pct = self.nearest_level(price)
        if name in ("+1.372", "-1.372") and dist_pct <= pct:
            return name
        # Also flag +1.272 / -1.272 as "approaching extreme"
        if name in ("+1.272", "-1.272") and dist_pct <= pct:
            return name
        return None


def envelope_from_morning(
    morning_open: float,
    morning_high: float,
    morning_low: float,
) -> FibEnvelope:
    """Create envelope from session open and morning range.

    Anchor = morning_open.  Range high/low = extremes of the morning session.
    """
    return FibEnvelope(
        anchor=morning_open,
        range_high=morning_high,
        range_low=morning_low,
        direction="long" if morning_high - morning_open > morning_open - morning_low else "short",
    )


def envelope_from_range(
    range_high: float,
    range_low: float,
) -> FibEnvelope:
    """Create envelope anchored at the midpoint of the range."""
    anchor = (range_high + range_low) / 2.0
    return FibEnvelope(
        anchor=anchor,
        range_high=range_high,
        range_low=range_low,
        direction="long",
    )


# ── summary renderer ───────────────────────────────────────────────────

def render_envelope(env: FibEnvelope, current_price: Optional[float] = None) -> str:
    """Return a formatted string showing the envelope and price position."""
    lvls = env.levels()
    lines = []
    lines.append(f"  GOLDEN FIB ENVELOPE (range {env.range_low:.2f}–{env.range_high:.2f}, size {env.range_size:.2f})")
    lines.append("")

    # Sort levels from highest to lowest
    key_levels = ["+1.372", "+1.272", "+1.000", "+0.729", "+0.618", "+0.508",
                  "0.000", "-0.508", "-0.618", "-0.729", "-1.000", "-1.272", "-1.372"]
    for name in key_levels:
        if name not in lvls:
            continue
        lvl = lvls[name]
        marker = ""
        if current_price is not None:
            dist = abs(current_price - lvl)
            if dist <= env.range_size * 0.005:
                marker = " ◀══ PRICE IS HERE"
            elif dist <= env.range_size * 0.02:
                marker = "  ← approaching"
        lines.append(f"    {name:>7s}  {lvl:>10.2f}{marker}")

    if current_price is not None:
        name, _, dist_pct = env.nearest_level(current_price)
        lines.append("")
        lines.append(f"  Current: {current_price:.2f}  →  nearest: {name} ({dist_pct:.1f}% of range)")

        extreme = env.is_at_extreme(current_price)
        if extreme:
            lines.append(f"  ⚠️ AT EXTREME: {extreme} — exhaustion zone")

    return "\n".join(lines)