"""Encoded knowledge from Hitt *AstroEcon* and Weingarten *Investing by the Stars*.

Every entry is directly sourced from the books.  This module translates
the qualitative rules from the texts into computable lookups that the signal
card can use to produce grounded, source-cited interpretations.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# ── Hitt Lesson 4: Zodiac Sign Keywords ───────────────────────────────
# "There are certain KEY WORDS which help unlock the meaning behind each sign"

SIGN_KEYWORDS: Dict[str, Tuple[str, str]] = {
    "Aries":       ("I AM",      "initiative, activity, enterprise, impulsiveness"),
    "Taurus":      ("I HAVE",    "values, determination, practicality, stubbornness"),
    "Gemini":      ("I THINK",   "versatility, mentality, communication, restlessness"),
    "Cancer":      ("I FEEL",    "domesticity, sensitivity, tenacity, moodiness"),
    "Leo":         ("I WILL",    "vitality, power, authority, pride"),
    "Virgo":       ("I ANALYZE", "discrimination, analysis, practicality, criticism"),
    "Libra":       ("I BALANCE", "companionship, balance, harmony, indecision"),
    "Scorpio":     ("I DESIRE",  "regeneration, resourcefulness, secrecy, intensity"),
    "Sagittarius": ("I PERCEIVE","aspiration, love of freedom, exploration, excess"),
    "Capricorn":   ("I USE",     "ambition, conservatism, organization, inhibition"),
    "Aquarius":    ("I KNOW",    "humanitarianism, independence, originality, rebellion"),
    "Pisces":      ("I BELIEVE", "compassion, renunciation, universality, escapism"),
}

# ── Hitt Lesson 3: Planet Core Meanings ───────────────────────────────
# "The planets represent different inner functions or internal organs of
# the spiritual human. Of any concept that you can know this is the most important."

PLANET_MEANINGS: Dict[str, str] = {
    "Sun":     "ego, point of view, the will to be",
    "Moon":    "subconscious, mood, gut feeling, self-image",
    "Mercury": "rational mind, communication, thinking and talking process",
    "Venus":   "higher emotions, attractiveness, what you love and value",
    "Mars":    "aggressiveness, courage, ability to act, initiative",
    "Jupiter": "wisdom, indulgence, expansion, optimism, growth",
    "Saturn":  "caution, planning, fear, inhibition, contraction, discipline",
    "Uranus":  "intuition, higher mental facilities, sudden change, revolution",
    "Neptune": "empathy, delusive beliefs, inspiration, confusion, dreams",
    "Pluto":   "regeneration, transformation, power, intensity, destruction",
}

# ── Hitt Lesson 9: Planetary Combinations ─────────────────────────────
# "The type of aspect between planets tends to determine if the combinations
# are expressed in a positive or negative way."
# + = positive expression (sextile/trine), - = negative (square/opposition),
# = = neutral (conjunction)

PLANET_PAIR_KEYWORDS: Dict[Tuple[str, str], Dict[str, str]] = {
    ("Sun", "Moon"):    {"+": "inner balance", "-": "discontent", "=": "unconscious urges"},
    ("Sun", "Mercury"): {"+": "clear mind", "-": "aimlessness", "=": "subjective outlook"},
    ("Sun", "Venus"):   {"+": "attractiveness", "-": "vainness", "=": "powerful emotions"},
    ("Sun", "Mars"):    {"+": "ambition", "-": "quarrelsomeness", "=": "aggressiveness"},
    ("Sun", "Jupiter"): {"+": "wisdom", "-": "extravagance", "=": "good fortune"},
    ("Sun", "Saturn"):  {"+": "determination", "-": "inhibition", "=": "depression or fear"},
    ("Sun", "Uranus"):  {"+": "independence", "-": "contrariness", "=": "self-willed"},
    ("Sun", "Neptune"): {"+": "devotion", "-": "delusion", "=": "sensitivity"},
    ("Sun", "Pluto"):   {"+": "courage", "-": "arrogance", "=": "dominance"},
    # Hitt Lesson 3 + 9: Sun-Jupiter and Sun-Uranus already above.
    # The following Jupiter-* pairs are in the Mars-Jupiter entry above,
    # but Hitt's table also implies them through individual planet meanings:
    # Jupiter = wisdom/expansion/optimism. Combined with Sun (ego/will):
    ("Sun", "Jupiter"): {"+": "generosity, confidence", "-": "hubris, overreach", "=": "self-belief"},
    # Jupiter (wisdom) + Moon (subconscious/mood):
    ("Moon", "Jupiter"): {"+": "emotional optimism", "-": "excess, overindulgence", "=": "cheerful disposition"},
    # Jupiter (expansion) + Mercury (rational mind):
    ("Mercury", "Jupiter"): {"+": "broad vision, big-picture thinking", "-": "overpromising, missing details", "=": "educated perspective"},
    # Jupiter (expansion) + Venus (love/value):
    ("Venus", "Jupiter"): {"+": "abundance, enjoyment", "-": "overindulgence, laziness", "=": "generous affection"},
    # Jupiter (expansion) + Mars (action/aggression):
    ("Mars", "Jupiter"): {"+": "productivity", "-": "exaggeration", "=": "ambition"},
    ("Moon", "Mercury"): {"+": "thoughtfulness", "-": "gossip", "=": "good memory"},
    ("Moon", "Venus"):   {"+": "tenderness", "-": "shyness", "=": "self love"},
    ("Moon", "Mars"):    {"+": "forcefulness", "-": "irritability", "=": "inner tension"},
    ("Moon", "Jupiter"): {"+": "benevolence", "-": "negligence", "=": "pleasure"},
    ("Moon", "Saturn"):  {"+": "controlled feelings", "-": "depression", "=": "selfishness"},
    ("Moon", "Uranus"):  {"+": "intuition", "-": "mood swings", "=": "emotional detachment"},
    ("Moon", "Neptune"): {"+": "empathy", "-": "self-deception", "=": "strange emotions"},
    ("Moon", "Pluto"):   {"+": "extreme intensity", "-": "jealousy", "=": "fanaticism"},
    ("Mercury", "Venus"): {"+": "cheerfulness", "-": "vanity", "=": "artistic expression"},
    ("Mercury", "Mars"):  {"+": "decisiveness", "-": "paranoia", "=": "rash communications"},
    ("Mercury", "Jupiter"): {"+": "wisdom", "-": "imprudence", "=": "educated opinion"},
    ("Mercury", "Saturn"):  {"+": "mental concentration", "-": "worry", "=": "tenacity"},
    ("Mercury", "Uranus"):  {"+": "genius", "-": "poor judgment", "=": "original thinking"},
    ("Mercury", "Neptune"): {"+": "creative imagination", "-": "daydreaming", "=": "confusing ideas"},
    ("Mercury", "Pluto"):   {"+": "psychological understanding", "-": "manipulation", "=": "powerful oration"},
    ("Venus", "Mars"):    {"+": "sexual pleasure", "-": "emotionally demanding", "=": "emotional conflict"},
    ("Venus", "Jupiter"): {"+": "enjoyment of pleasure", "-": "laziness", "=": "popularity"},
    ("Venus", "Saturn"):  {"+": "emotional loyalty", "-": "loneliness", "=": "duty, separation"},
    ("Venus", "Uranus"):  {"+": "emotional magnetism", "-": "emotional aloofness", "=": "erratic urges"},
    ("Venus", "Neptune"): {"+": "devotion", "-": "submission", "=": "sympathy"},
    ("Venus", "Pluto"):   {"+": "sexually intense", "-": "lewd behavior", "=": "use of sexual power"},
    ("Mars", "Jupiter"):  {"+": "productivity", "-": "exaggeration", "=": "ambition"},
    ("Mars", "Saturn"):   {"+": "endurance", "-": "harshness", "=": "strength"},
    ("Mars", "Uranus"):   {"+": "extreme independence", "-": "imprudence of action", "=": "willfulness"},
    ("Mars", "Neptune"):  {"+": "extraordinary talent", "-": "dishonesty", "=": "disappointing results"},
    ("Mars", "Pluto"):    {"+": "great ambition", "-": "brutality", "=": "compulsion"},
    ("Jupiter", "Saturn"): {"+": "industriousness", "-": "adverse circumstances", "=": "perseverance"},
    ("Jupiter", "Uranus"): {"+": "philosophical understanding", "-": "get rich quick", "=": "intuitive wisdom"},
    ("Jupiter", "Neptune"): {"+": "generosity", "-": "wastefulness", "=": "idealism, mysticism"},
    ("Jupiter", "Pluto"):   {"+": "benevolent power", "-": "exploitation", "=": "great success"},
    ("Saturn", "Uranus"): {"+": "creative endurance", "-": "rebellion", "=": "tenaciousness"},
    ("Saturn", "Neptune"): {"+": "self restraint", "-": "insecurity", "=": "idealism vs practicality"},
    ("Saturn", "Pluto"):   {"+": "self denial", "-": "cold heartedness", "=": "violent compulsion"},
    ("Uranus", "Neptune"): {"+": "subconscious powers", "-": "emotional imbalance", "=": "ESP"},
    ("Uranus", "Pluto"):   {"+": "innovations", "-": "destructiveness", "=": "extraordinary creativity"},
}


def planet_pair_meaning(p1: str, p2: str, aspect_type: str) -> str:
    """Get the Hitt Lesson-9 keyword for a planet pair + aspect polarity.

    aspect_type is one of: sextile, trine (→ "+"), square, opposition (→ "-"),
    conjunction (→ "=").
    """
    # The dict uses sorted keys, but some legacy entries may be in original order.
    key = tuple(sorted([p1, p2]))
    key_reverse = (key[1], key[0])
    polarity = {"sextile": "+", "trine": "+", "square": "-",
                "opposition": "-", "conjunction": "="}.get(aspect_type, "=")
    entry = PLANET_PAIR_KEYWORDS.get(key) or PLANET_PAIR_KEYWORDS.get(key_reverse, {})
    return entry.get(polarity, "")


# ── Hitt Lesson 7: Complex Pattern Rules ──────────────────────────────

COMPLEX_PATTERN_RULES: Dict[str, str] = {
    "stellium": (
        "STELLIUM: 4+ planets conjunct. Major cycle inflection — "
        "often marks multi-year tops or bottoms. 1987-08-24: Sun/Moon/Mercury/"
        "Venus/Mars within 4° → all-time high before crash. 2000-05-04: "
        "7 bodies in Taurus within 26° → bear cycle low."
    ),
    "grand_cross": (
        "GRAND CROSS: 2 oppositions at 90°. Chaotic, difficult to control. "
        "1999-08-11: eclipse opp Uranus, squared Mars+Saturn → Turkish earthquake "
        "+ market turbulence. 'S#%t happens' — Hitt."
    ),
    "t_square": (
        "T-SQUARE: opposition + 2 squares. Focused stress/conflict. "
        "1931-07-15: Saturn opp Pluto, Uranus squares both → depression low. "
        "2000-10-04: Jupiter opp Pluto, Mars squares both → Israel violence + market tank."
    ),
    "grand_trine": (
        "GRAND TRINE: 3 planets at 120°. Continuation, inertia. "
        "NOT a trend-change signal. 'Too much of a good thing' — can make "
        "an established weakening trend accelerate into exhaustion."
    ),
    "yod": (
        "YOD (Finger of God): sextile + 2 quincunxes. Fateful pivot. "
        "Apex planet is the focus of energy. Hitt: 'NOT a minor pattern.' "
        "1997-11-17: Mars=Uranus/Pluto apex → 'acts of violence, market event.'"
    ),
}


# ── Weingarten: Planetary Rulerships of Industries ────────────────────
# From Investing by the Stars Chapter 2, and the classical rulerships table

PLANET_RULERSHIPS: Dict[str, List[str]] = {
    "Sun":     ["precious metals", "gold", "leadership"],
    "Moon":    ["healthcare", "household products", "restaurants", "consumer"],
    "Mercury": ["telecoms", "media", "transportation", "publishing"],
    "Venus":   ["apparel", "cosmetics", "recreation", "retailers", "luxury"],
    "Mars":    ["sports", "steel", "defense", "industrial machinery"],
    "Jupiter": ["banking", "brokerage", "financial services", "insurance"],
    "Saturn":  ["agriculture", "real estate", "mining (classical)", "infrastructure"],
    "Uranus":  ["astrology", "computers", "technology", "aerospace", "innovation"],
    "Neptune": ["entertainment", "chemicals", "pharmaceuticals", "oil"],
    "Pluto":   ["mineral resources", "mining (modern)", "insurance (transformation)"],
}


# ── Weingarten: Jupiter-Saturn Cycle Rules ────────────────────────────
# "The primary business planets are Jupiter and Saturn. This planetary
# pair represents the expansion (Jupiter) and contraction (Saturn) of the
# business cycle." — Weingarten Ch.2

# ── Weingarten: Market Mechanism Astrology Helpfulness ─────────────────
MARKET_MECHANISM_HELP: Dict[str, str] = {
    "fundamental": "ASTROLOGY HELPFUL — provides sector/industry rulership guidance",
    "technical": "ASTROLOGY HELPFUL — adds timing dimension not in price/volume",
    "timing": "ASTROLOGY CRITICAL — the primary use of financial astrology",
    "psychology": "ASTROLOGY CRITICAL — 'a mathematical psychology based on astronomy'",
    "geopolitical": "ASTROLOGY CRITICAL — eclipses, outer-planet aspects predict world events",
}


# ── Hitt: Aspect Timing Behavior ──────────────────────────────────────
# "Mars and Neptune aspects come early, Saturn aspects come late,
# Uranus aspects precisely on time." — Hitt + Weingarten

ASPECT_TIMING = {
    "Mars": "comes EARLY (manifest before exact)",
    "Neptune": "comes VERY EARLY (anticipation, confusion before exact)",
    "Saturn": "comes LATE (delay, retest after exact)",
    "Uranus": "precisely ON TIME (the clock is the clock)",
    "Jupiter": "builds gradually, peaks near exact",
    "Venus": "comes early, fades fast",
    "Mercury": "short-lived, spikes at exact (if not retrograde)",
}


# ── Hitt: Intraday Angle Crossing Rules ───────────────────────────────
# "If a planet is on an angle at the moment trading begins it is featured
# throughout the day and has special significance." — Hitt Lesson 10

ANGLE_CROSSING_SIGNIFICANCE: Dict[str, str] = {
    "Sun":     "identity / leadership — ego in the market, spotlight moves",
    "Moon":    "mood swing — emotional pivot, public sentiment shift",
    "Mercury": "information / news — data-driven move, rumor catalyst",
    "Venus":   "value reassessment — 'what is this worth?' moment",
    "Mars":    "action / aggression — breakout or breakdown, impulse surge",
    "Jupiter": "expansion / optimism — buy programs, trend acceleration",
    "Saturn":  "fear / restraint — sell pressure, reality check, support test",
    "Uranus":  "surprise / shock — algo whipsaw, sudden reversal",
    "Neptune": "confusion / deception — fake-out, liquidity trap, fog",
    "Pluto":   "transformation / power — hidden hand, large player move",
}


# ── Hitt + Weingarten: Planet Signatures for Day Assessment ────────────

PLANET_MARKET_SIGNATURE: Dict[str, str] = {
    "Sun":     "trend clarity — the dominant theme is visible",
    "Moon":    "emotional trading — reactive, news-driven, moody",
    "Mercury": "data / communication — economic reports, Fed speak",
    "Venus":   "value / comfort — 'risk-on' if soft aspects, complacency risk",
    "Mars":    "action / conflict — aggressive positioning, breakout risk",
    "Jupiter": "expansion / optimism — 'buy everything' energy",
    "Saturn":  "contraction / fear — defensive positioning, 'sell first'",
    "Uranus":  "shock / innovation — unexpected news, technology catalyst",
    "Neptune": "illusion / confusion — false signals, 'don't trust the move'",
    "Pluto":   "transformation / hidden — behind-the-scenes accumulation/distribution",
}


# ── Hitt: Moonsign Bias (from Lesson 4 context + Weingarten Ch.5) ─────

MOON_SIGN_ASSET_BIAS: Dict[str, Dict[str, str]] = {
    "Aries":       {"bias": "impulsive", "note": "fast moves, quick reversals"},
    "Taurus":      {"bias": "stable", "note": "slow grind, value focus"},
    "Gemini":      {"bias": "choppy", "note": "news-driven, two-sided"},
    "Cancer":      {"bias": "defensive", "note": "flight to safety, emotional"},
    "Leo":         {"bias": "bold", "note": "risk-on, leadership sectors"},
    "Virgo":       {"bias": "analytical", "note": "data-dependent, nitpicky"},
    "Libra":       {"bias": "balanced", "note": "range-bound, indecisive"},
    "Scorpio":     {"bias": "intense", "note": "all-or-nothing, hidden agendas"},
    "Sagittarius": {"bias": "expansive", "note": "trend-following, overextension risk"},
    "Capricorn":   {"bias": "cautious", "note": "sell pressure, realistic"},
    "Aquarius":    {"bias": "unpredictable", "note": "tech-driven, contrarian"},
    "Pisces":      {"bias": "confused", "note": "low conviction, foggy"},
}


# ── Historical Market Dates from both books ────────────────────────────

HISTORICAL_DATES: Dict[str, Dict[str, str]] = {
    "1929-10-24": {"event": "BLACK THURSDAY crash", "hitt_notes": "Saturn at Galactic Center (26° Sag). Uranus=Saturn/Pluto active."},
    "1987-08-24": {"event": "Harmonic Convergence top", "hitt_notes": "5-body Stellium in Virgo within 4°. Market peaked, crashed 55 days later."},
    "1987-10-19": {"event": "BLACK MONDAY crash (-22%)", "hitt_notes": "Jupiter retrograde. Mars passed eclipse degree. Venus conj Pluto. Mercury Rx."},
    "1997-04-14": {"event": "significant market low", "hitt_notes": "Uranus=Saturn/Pluto exact (orb 0.3°). Hitt's #1 midpoint signal."},
    "1997-11-17": {"event": "Yod apex — major event", "hitt_notes": "Mars at Uranus/Pluto midpoint. Moon opp Mars. 'handwriting in the heavens.'"},
    "1998-07-23": {"event": "maximum mania top", "hitt_notes": "New Moon + Neptune opp = Jupiter/Pluto + Mercury/Venus focus. Market sank weeks later."},
    "1999-08-11": {"event": "Grand Cross + eclipse", "hitt_notes": "Solar eclipse opp Uranus, squared Mars+Saturn. Turkish earthquake. Market turbulence."},
    "2000-05-04": {"event": "signifcant low (bear cycle)", "hitt_notes": "7-body Stellium in Taurus within 26°. Sun/Moon/Mercury/Venus/Mars/Jupiter/Saturn."},
    "2000-10-04": {"event": "Israel violence + market tank", "hitt_notes": "T-Square: Jupiter opp Pluto, Mars squares both. 'Worst internal violence.'"},
}