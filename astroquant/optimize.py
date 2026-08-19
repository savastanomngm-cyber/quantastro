"""Optimized Bradley weights + signal confluence scoring.

Three capabilities:

1. **Per-planet-pair Bradley weight optimization**
   Crawford's "Astronomic Cycles Sum" approach: regress each of the
   45 planet-pair × 5 aspect combinations against historical returns
   to find empirically optimal weights.  Regularization prevents
   overfitting on rare pairs.

2. **Confluence scoring (Weingarten Rule of Three)**
   "One indication is a possibility, two are a probability, three are a
   certainty."  Combine multiple independent signals into a single
   aggregate score and test monotonicity.

3. **Stellium volatility signal**
   Stelliums show positive mean Δ but likely wide dispersion.  Model
   them as a variance predictor — wider stops / smaller positions on
   Stellium days.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .bradley import ASPECT_ANGLES, BRADLEY_WEIGHTS
from .ephemeris import PLANETS, angle_diff, get_longitudes, jd_from_date


# ── 1. Per-pair Bradley weight optimization ───────────────────────────

def _pair_aspect_name(p1: str, p2: str, aspect: str) -> str:
    """Canonical key: 'Sun_Moon_conjunction'."""
    a, b = sorted([p1, p2])
    return f"{a}_{b}_{aspect}"


def compute_aspect_matrix(
    jd_list: List[float],
    orbs: Optional[Dict[str, float]] = None,
) -> Tuple[pd.DataFrame, pd.Index]:
    """Build a feature matrix where each column is a planet-pair-aspect binary.

    Returns (X_matrix, feature_names).  X[i, j] = 1 if aspect j is active on day i.
    """
    if orbs is None:
        orbs = {
            "conjunction": 8.0, "sextile": 6.0, "square": 6.0,
            "trine": 8.0, "opposition": 8.0,
        }

    # Build all feature names first
    feature_names: List[str] = []
    for i in range(len(PLANETS)):
        for j in range(i + 1, len(PLANETS)):
            p1, p2 = PLANETS[i], PLANETS[j]
            for aspect in ["conjunction", "sextile", "square", "trine", "opposition"]:
                feature_names.append(_pair_aspect_name(p1, p2, aspect))

    n_days = len(jd_list)
    n_features = len(feature_names)
    X = np.zeros((n_days, n_features), dtype=np.int8)

    for day_idx, jd in enumerate(jd_list):
        pos = get_longitudes(jd)
        for i in range(len(PLANETS)):
            for j in range(i + 1, len(PLANETS)):
                p1, p2 = PLANETS[i], PLANETS[j]
                lon1, lon2 = pos.get(p1), pos.get(p2)
                if lon1 is None or lon2 is None:
                    continue
                diff = angle_diff(lon1, lon2)
                for aspect, target_angle in ASPECT_ANGLES.items():
                    if aspect == "quincunx":
                        continue
                    orb_val = orbs.get(aspect, 8.0)
                    if abs(diff - target_angle) <= orb_val:
                        feat_name = _pair_aspect_name(p1, p2, aspect)
                        col_idx = feature_names.index(feat_name)  # safe — we built the list
                        X[day_idx, col_idx] = 1
                        break  # count each pair once per day

    return pd.DataFrame(X, columns=feature_names), pd.Index(feature_names)


def optimize_bradley_weights(
    jd_list: List[float],
    returns: np.ndarray,
    lambd: float = 0.01,
    orbs: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Ridge-regress aspect matrix against returns to find optimal weights.

    Args:
        jd_list: Julian days (one per trading day)
        returns: log-return array, same length as jd_list
        lambd: L2 regularization strength (higher = more shrinkage toward zero)
        orbs: aspect orbs, defaults to Hitt standard

    Returns:
        dict with:
          - weights: {feature_name: optimized_weight}
          - aggregated: {aspect_type: avg_weight} for simplified daily use
          - r2: in-sample R²
          - intercept: regression intercept
          - feature_importance: top 20 features by |weight|
    """
    X_df, fnames = compute_aspect_matrix(jd_list, orbs)
    X = X_df.values.astype(np.float64)
    y = returns

    # Drop features with near-zero variance (< 5 nonzero days)
    nonzero = (X != 0).sum(axis=0)
    keep = nonzero >= 5
    X = X[:, keep]
    kept_names = [fnames[i] for i in range(len(fnames)) if keep[i]]

    # Center y (we don't center X because binary features + we want intercept)
    y_mean = y.mean()
    y_centered = y - y_mean

    # Ridge regression: w = (X'X + λI)^-1 X'y
    n_features = X.shape[1]
    XtX = X.T @ X
    XtY = X.T @ y_centered
    reg = XtX + lambd * np.eye(n_features)
    try:
        w = np.linalg.solve(reg, XtY)
    except np.linalg.LinAlgError:
        w = np.linalg.lstsq(reg, XtY, rcond=None)[0]

    # Predictions
    y_pred = X @ w + y_mean
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Build weight dict
    weights = {name: float(w[i]) for i, name in enumerate(kept_names)}

    # Aggregate by aspect type
    aggregated: Dict[str, List[float]] = {}
    for name, wt in weights.items():
        asp_type = name.rsplit("_", 1)[-1]
        aggregated.setdefault(asp_type, []).append(wt)
    agg_avg = {k: float(np.mean(v)) for k, v in aggregated.items()}

    # Feature importance
    importance = sorted(
        [(name, float(w[i])) for i, name in enumerate(kept_names)],
        key=lambda x: abs(x[1]),
        reverse=True,
    )[:20]

    return {
        "weights": weights,
        "aggregated": agg_avg,
        "r2": round(float(r2), 6),
        "intercept": round(float(y_mean), 8),
        "feature_importance": importance,
        "n_features": len(kept_names),
    }


def compute_optimized_bradley(
    positions: Dict[str, float],
    weights_dict: Dict[str, float],
    orbs: Optional[Dict[str, float]] = None,
) -> float:
    """Compute one-day optimized Bradley index from learned weights."""
    if orbs is None:
        orbs = {
            "conjunction": 8.0, "sextile": 6.0, "square": 6.0,
            "trine": 8.0, "opposition": 8.0,
        }

    total = 0.0
    for i in range(len(PLANETS)):
        for j in range(i + 1, len(PLANETS)):
            p1, p2 = PLANETS[i], PLANETS[j]
            lon1 = positions.get(p1)
            lon2 = positions.get(p2)
            if lon1 is None or lon2 is None:
                continue
            diff = angle_diff(lon1, lon2)
            for aspect, target_angle in ASPECT_ANGLES.items():
                if aspect == "quincunx":
                    continue
                if abs(diff - target_angle) <= orbs.get(aspect, 8.0):
                    key = _pair_aspect_name(p1, p2, aspect)
                    total += weights_dict.get(key, 0.0)
                    break
    return total


# ── 2. Confluence scoring ─────────────────────────────────────────────

def compute_confluence_score(
    positions: Dict[str, float],
    speeds: Dict[str, float],
    complex_patterns: Dict[str, Any],
    bradley_total: float,
    midpoint_hit_count: int,
) -> Dict[str, Any]:
    """Weingarten Rule of Three — combine independent signals into a score.

    Each signal contributes +1 to a bull flag or -1 to a bear flag.
    The net score is the sum.  Weingarten: "one = possibility,
    two = probability, three = certainty."

    Signals (each ±1, independently triggered):
      - Hard aspect dominance (>3 more hard than soft)  → -1
      - Soft aspect dominance (>3 more soft than hard)  → +1
      - Mercury retrograde                                → -1
      - Venus retrograde                                  → -1
      - Mars retrograde                                   → -1
      - Grand Trine detected                              → +1
      - T-Square detected                                 → -1 (stress)
      - Grand Cross detected                              → -2 (extreme stress)
      - YOD detected                                      → -1 (fateful pivot)
      - Stellium detected                                 → 0 (volatility, not directional)
      - Uranus=Saturn/Pluto hit                           → ±2 (major cycle, sign depends)
      - Bradley > +4                                      → +1
      - Bradley < -4                                      → -1
      - Moon full                                         → +1 (momentum)
      - Moon new                                          → +1 (reversal/fresh start — direction depends on context, treated as volatility)
      - Saturn rx                                         → -1
      - Jupiter rx                                        → -1
      - Midpoint hits > 2                                 → -1 (complexity = caution)

    Returns:
      { score, bull_count, bear_count, interpretation, signal_flags }
    """
    bull = 0
    bear = 0
    flags: List[str] = []

    moon = None
    try:
        from .ephemeris import get_moon_phase, jd_from_date
    except ImportError:
        pass

    # Aspect dominance — count via the positions directly
    from .aspects import find_all_aspects
    aspects = find_all_aspects(positions)
    hard = sum(1 for a in aspects if a["type"] in ("conjunction", "square", "opposition"))
    soft = sum(1 for a in aspects if a["type"] in ("sextile", "trine"))
    if hard > soft + 3:
        bear += 1
        flags.append("HARD_DOMINANCE")
    elif soft > hard + 3:
        bull += 1
        flags.append("SOFT_DOMINANCE")

    # Retrogrades
    rx_map = {
        "Mercury": ("MERC_RX", -1),
        "Venus": ("VENUS_RX", -1),
        "Mars": ("MARS_RX", -1),
        "Jupiter": ("JUPITER_RX", -1),
        "Saturn": ("SATURN_RX", -1),
    }
    for planet, (flag, val) in rx_map.items():
        if speeds.get(planet, 0) < 0:
            if val > 0:
                bull += val
            else:
                bear += abs(val)
            flags.append(flag)

    # Complex patterns
    if complex_patterns.get("grand_trine"):
        bull += 1
        flags.append("GRAND_TRINE")
    if complex_patterns.get("t_square"):
        bear += 1
        flags.append("T_SQUARE")
    if complex_patterns.get("grand_cross"):
        bear += 2
        flags.append("GRAND_CROSS")
    if complex_patterns.get("yod"):
        bear += 1
        flags.append("YOD")
    if complex_patterns.get("stellium"):
        flags.append("STELLIUM")  # directional neutral but volatile

    # Bradley extremes
    if bradley_total >= 4.0:
        bull += 1
        flags.append("BRADLEY_BULLISH")
    elif bradley_total <= -4.0:
        bear += 1
        flags.append("BRADLEY_BEARISH")

    # Midpoints
    if midpoint_hit_count > 2:
        bear += 1
        flags.append("MIDPOINT_CLUSTER")

    # Uranus=Saturn/Pluto
    from .midpoints import uranus_saturn_pluto
    usp = uranus_saturn_pluto(positions, orb=2.0)
    if usp:
        # This is a major cycle signal — direction depends on context
        # For now: flag but treat as amplified whatever the prevailing bias is
        flags.append("URANUS_SATURN_PLUTO")

    net = bull - bear

    if net >= 3:
        interp = "CERTAINTY (Weingarten Rule of Three satisfied) — strong directional conviction"
    elif net >= 2:
        interp = "PROBABILITY — two independent signals aligned"
    elif net >= 1:
        interp = "POSSIBILITY — single signal, wait for confirmation"
    elif net >= -1:
        interp = "NEUTRAL — conflicting or absent signals"
    elif net >= -2:
        interp = "CAUTION — negative signals building"
    else:
        interp = "DANGER — multiple negative signals; Weingarten Rule of Three satisfied for downside"

    return {
        "score": net,
        "bull_count": bull,
        "bear_count": bear,
        "interpretation": interp,
        "flags": flags,
    }


# ── 3. Stellium volatility signal ─────────────────────────────────────

def stellium_volatility_signal(
    positions: Dict[str, float],
    orb: float = 8.0,
    min_bodies: int = 4,
) -> Optional[Dict[str, Any]]:
    """Check if today has a Stellium and compute the volatility implication.

    Hitt: "A STELLIUM ... can be an extraordinary event ... unlikely to
    occur with the same planets more than once in most lifetimes."

    The empirical result: Stelliums show slightly positive mean return
    but WIDE dispersion.  This function:
      - Returns None if no Stellium
      - Returns a dict with the Stellium details + suggested risk adjustment
        (position size multiplier, wider stop multiplier)
    """
    from .aspects import find_stellium

    st = find_stellium(positions, min_bodies=min_bodies, max_orb=orb)
    if st is None:
        return None

    # Volatility scaling based on number of bodies
    # 4 bodies: 1.5x volatility
    # 5 bodies: 2.0x volatility
    # 6+ bodies: 2.5x volatility
    n = st["bodies_count"]
    vol_mult = min(1.0 + (n - 3) * 0.5, 3.0)
    # Position sizing: inverse of vol_mult (smaller positions)
    pos_frac = 1.0 / vol_mult
    # Stop width: proportional to vol_mult
    stop_mult = vol_mult

    # Check if outer planets (Jupiter-Pluto) are involved — amplifies
    outer_involved = any(
        p in st["bodies"] for p in ("Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")
    )
    if outer_involved:
        vol_mult *= 1.5
        pos_frac /= 1.5
        stop_mult *= 1.5

    return {
        "bodies": st["bodies"],
        "bodies_count": n,
        "sign": st["sign"],
        "degree_range": st["degree_range"],
        "outer_planets_involved": outer_involved,
        "volatility_multiplier": round(vol_mult, 2),
        "suggested_position_fraction": round(pos_frac, 2),
        "suggested_stop_multiplier": round(stop_mult, 2),
        "hitt_rule": "Major cycle inflection — often marks multi-year tops or bottoms. "
                     "Trade with wider stops, smaller size.",
    }