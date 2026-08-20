#!/usr/bin/env python3
"""GOLDEN FIB + ASTRO SYSTEM — interactive terminal menu.

One app, full control. Type a date (YYYY-MM-DD), pick options,
everything in one place.

Usage:  python3 menu.py
"""

import os
import sys
import subprocess
from datetime import datetime, timedelta

# ── styling ────────────────────────────────────────────────────────────
C = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "bg_blue": "\033[44m",
    "bg_green": "\033[42m",
    "bg_red": "\033[41m",
}
W = 66
HR = "─" * W

BANNER = rf"""{C['yellow']}
  ╔══════════════════════════════════════════════════════════════╗
  ║   GOLDEN FIB + ASTRO TRADING SYSTEM                          ║
  ║   fib = where · astro = how much · hold 3-5d                 ║
  ╚══════════════════════════════════════════════════════════════╝{C['reset']}
"""


def valid_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def ask_date() -> str:
    while True:
        d = input(f"{C['cyan']}Date (YYYY-MM-DD){C['reset']} or b = back: ").strip()
        if d.lower() in ("b", "back", ""):
            return None
        if valid_date(d):
            return d
        print(f"{C['red']}  ✗ Invalid — use YYYY-MM-DD like 2026-08-19{C['reset']}")


def ask_asset() -> str:
    while True:
        a = input(f"{C['cyan']}Asset{C['reset']} [ES/NQ/GC] (b=back): ").strip().upper()
        if a.lower() in ("b", "back"):
            return None
        if a in ("ES", "NQ", "GC"):
            return a
        print(f"{C['red']}  ✗ Pick ES (S&P), NQ (Nasdaq), or GC (Gold){C['reset']}")


def ticker_for(asset: str) -> str:
    return {"ES": "SPY", "NQ": "QQQ", "GC": "GLD"}[asset]


def fetch_prev_day(asset: str, date_str: str):
    """Auto-fetch OHLC info for the given date.

    Returns dict with:
      - previous trading day's OHLC (the ANCHOR candle)
      - current_close: the typed date's close IF it has already closed,
        else None (date hasn't traded yet → planning mode).
    yfinance end is EXCLUSIVE, so we fetch through date+1 to include the
    typed date when it exists.
    """
    import yfinance as yf
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    start = (dt - timedelta(days=8)).strftime("%Y-%m-%d")
    end = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
    data = yf.download(ticker_for(asset), start=start, end=end, progress=False)
    if len(data) < 1:
        return None
    tk = ticker_for(asset)
    last = data.iloc[-1]
    last_date = data.index[-1].strftime("%Y-%m-%d")

    current_close = None
    if last_date == date_str and len(data) >= 2:
        current_close = float(last[("Close", tk)])
        prev = data.iloc[-2]
        anchor_date = data.index[-2].strftime("%Y-%m-%d")
    else:
        prev = last
        anchor_date = last_date

    return {
        "open": float(prev[("Open", tk)]),
        "high": float(prev[("High", tk)]),
        "low": float(prev[("Low", tk)]),
        "close": float(prev[("Close", tk)]),
        "close_date": anchor_date,
        "current_close": current_close,
    }


# ── Option 1: FULL SIGNAL CARD ─────────────────────────────────────────
def opt_signal_card():
    print(f"\n{HR}\n  📊 DEEP-RESEARCH SIGNAL CARD\n{HR}")
    date_str = ask_date()
    if not date_str:
        return
    asset = ask_asset()
    if not asset:
        return

    # Try to auto-fetch yesterday's data for fib envelope
    prev = None
    try:
        prev = fetch_prev_day(asset, date_str)
    except Exception:
        pass

    cmd = [sys.executable, "-m", "astroquant.run", date_str]
    print(f"\n{'─'*W}")
    subprocess.run(cmd)

    # Fib envelope with real data if available
    if prev:
        print(f"\n{HR}\n  📐 GOLDEN FIB ENVELOPE (anchored on {prev['close_date']})\n{HR}")
        cmd2 = [
            sys.executable, "run_signals.py", date_str,
            "--open", str(prev["open"]),
            "--high", str(prev["high"]),
            "--low", str(prev["low"]),
            "--price", str(prev["current_close"] if prev["current_close"] is not None else prev["close"]),
        ]
        print()
        subprocess.run(cmd2)
        if prev["current_close"] is None:
            print(f"{C['yellow']}  ⚠ NOTE: {date_str} has no closed candle yet (planning ahead).\n"
                  f"  The envelope uses yesterday's close as a stand-in.\n"
                  f"  Re-run after the session closes for the real signal.{C['reset']}")
    else:
        print(f"{C['dim']}  (couldn't fetch yesterday's data — run run_signals.py manually with --open/--high/--low/--price){C['reset']}")

    input(f"\n{C['dim']}Press ENTER to continue...{C['reset']}")


# ── Option 2: Rulebook ────────────────────────────────────────────────
def run_rulebook():
    print(f"\n{HR}\n  ⚖️  RULEBOOK — direction & size\n{HR}")
    date_str = ask_date()
    if not date_str:
        return
    asset = ask_asset()
    if not asset:
        return

    if asset == "GC":
        print(f"\n  {C['yellow']}Note: this gives the ASTRO signal (date-based, reliable).\n"
              f"  For GC fib LEVELS use option 3, entering your chart's candle.{C['reset']}\n")
    cmd = [sys.executable, "run_rulebook.py", date_str, "--ticker", ticker_for(asset), "--asset", asset]
    subprocess.run(cmd)
    input(f"\n{C['dim']}Press ENTER to continue...{C['reset']}")


# ── Option 3: Fib anchor calculator ───────────────────────────────────
def run_fib_calc():
    print(f"\n{HR}\n  📐 GOLDEN FIB CALCULATOR\n{HR}")
    print("  Anchor: YESTERDAY's daily candle. 0 = LOW, 1 = HIGH.")
    date_str = ask_date()
    if not date_str:
        return
    asset = ask_asset()
    if not asset:
        return

    # Auto-fetch yesterday
    prev = None
    # For GC, NEVER auto-fetch — futures daily candles from yfinance use a
    # different globex session boundary than most brokers, so levels would
    # not match your chart.  Use the candle you SEE on your own chart.
    if asset == "GC":
        print(f"\n  {C['yellow']}GOLD (GC=F): enter the candle from YOUR chart.{C['reset']}")
        print(f"  {C['dim']}(yfinance futures bars don't match broker globex day-boundaries,\n"
              f"   so we use the exact LOW/HIGH you see to guarantee the grid is right){C['reset']}")
        while True:
            try:
                lo = float(input("  Yesterday's LOW : ").strip())
                hi = float(input("  Yesterday's HIGH: ").strip())
                if hi > lo:
                    break
                print("  HIGH must be > LOW")
            except ValueError:
                print("  Numbers only (e.g. 4330.7)")
        prev = {"high": hi, "low": lo, "close_date": "from-your-chart"}
    else:
        try:
            prev = fetch_prev_day(asset, date_str)
        except Exception:
            prev = None
        if prev:
            print(f"\n  Using yesterday ({prev['close_date']}):")
            print(f"    Open={prev['open']:.2f}  High={prev['high']:.2f}  Low={prev['low']:.2f}  Close={prev['close']:.2f}")
        else:
            print("\n  Enter yesterday's candle manually:")
            while True:
                try:
                    hi = float(input("  HIGH: ").strip())
                    lo = float(input("  LOW : ").strip())
                    if hi > lo:
                        break
                    print("  HIGH must be > LOW")
                except ValueError:
                    print("  Numbers only")
            prev = {"high": hi, "low": lo, "close_date": "manual"}

    R = prev["high"] - prev["low"]
    print(f"\n  RANGE = {R:.2f}\n")

    levels = [
        ("+1.372", prev["high"] + R * 0.372, "TAKE PROFIT"),
        ("+1.272", prev["high"] + R * 0.272, "approach"),
        ("+1.000", prev["high"], "yesterday's high"),
        ("+0.786", prev["low"] + R * 0.786, ""),
        ("+0.618", prev["low"] + R * 0.618, "golden"),
        ("+0.500", prev["low"] + R * 0.500, ""),
        ("+0.382", prev["low"] + R * 0.382, ""),
        ("+0.236", prev["low"] + R * 0.236, ""),
        (" 0.000", prev["low"], "yesterday's LOW"),
        ("-0.236", prev["low"] - R * 0.236, ""),
        ("-0.500", prev["low"] - R * 0.500, ""),
        ("-0.618", prev["low"] - R * 0.618, ""),
        ("-0.729", prev["low"] - R * 0.729, "1/γ"),
        ("-1.000", prev["low"] - R * 1.000, ""),
        ("-1.272", prev["low"] - R * 0.272, "BUY ZONE"),
        ("-1.372", prev["low"] - R * 0.372, "DEEP BUY"),
    ]
    for name, price, note in levels:
        glyph = C['green'] if 'BUY' in note or 'TAKE' in note else C['dim']
        print(f"  {name:>7}  {price:>10.2f}  {glyph}{note}{C['reset']}")
    input(f"\n{C['dim']}Press ENTER to continue...{C['reset']}")


# ── Option 4: Backtests ───────────────────────────────────────────────
def run_backtest_menu():
    while True:
        os.system("clear")
        print(f"{BANNER}")
        print(f"  {C['cyan']}BACKTESTS{C['reset']}")
        print(f"{HR}")
        print("   1. Fib extreme backtest (close-based)")
        print("   2. Rulebook backtest (position sizing)")
        print("   3. Anchor grid search (find best anchor)")
        print("   0. Back to main menu")
        print(HR)
        ch = input("  Choice: ").strip()
        if ch == "1":
            subprocess.run([sys.executable, "run_fib_backtest.py", "--ticker", "SPY"])
        elif ch == "2":
            subprocess.run([sys.executable, "run_rulebook_backtest.py", "--ticker", "SPY", "--asset", "ES"])
        elif ch == "3":
            subprocess.run([sys.executable, "run_anchor_backtest.py", "--ticker", "SPY"])
        elif ch == "0":
            return
        input(f"\n{C['dim']}Press ENTER...{C['reset']}")


# ── Option 5: CSV export ──────────────────────────────────────────────
def run_csv_export():
    print(f"\n{HR}\n  📊 EXPORT SIGNALS TO CSV\n{HR}")
    print("  Format: python3 run_backtest.py --start ... --end ... --ticker ... --signals [--csv path]")
    print(f"\n{C['cyan']}# Example:  python3 run_backtest.py --start 2018-01-01 --end 2026-08-01 --ticker SPY --signals --csv signals.csv")
    s = input(f"  Start (YYYY-MM-DD): ").strip()
    e = input(f"  End   (YYYY-MM-DD): ").strip()
    t = input(f"  Ticker (SPY/QQQ/GLD): ").strip().upper() or "SPY"
    opt = input(f"  Optimize weights? (y/n): ").strip().lower() == "y"
    if opt:
        subprocess.run([sys.executable, "run_backtest.py", "--start", s, "--end", e, "--ticker", t, "--signals", "--optimize"])
    else:
        subprocess.run([sys.executable, "run_backtest.py", "--start", s, "--end", e, "--ticker", t, "--signals"])
    input(f"\n{C['dim']}Press ENTER to continue...{C['reset']}")


# ── MAIN ──────────────────────────────────────────────────────────────
def main():
    while True:
        try:
            os.system("clear")
        except Exception:
            pass
        print(BANNER)
        print(f"  {C['bold']}MENU{C['reset']}" + " " * 22 + f"{C['dim']}Istanbul ~ {datetime.now().strftime('%H:%M')}{C['reset']}")
        print(HR)
        print("   1  📈  Daily signal card   (full astro + fib)")
        print("   2  ⚖️   Rulebook             (direction + size)")
        print("   3  📐  Fib calculator      (anchor + grid levels)")
        print("   4  🔬  Backtests           (IS/OOS validation)")
        print("   5  📊  CSV export          (signals to file)")
        print("   6  📖  House rules         (quick recap)")
        print("   0  🚪  Exit")
        print(HR)
        ch = input("  Choice: ").strip()

        if ch == "1":
            opt_signal_card()
        elif ch == "2":
            run_rulebook()
        elif ch == "3":
            run_fib_calc()
        elif ch == "4":
            run_backtest_menu()
        elif ch == "5":
            run_csv_export()
        elif ch == "6":
            print(f"\n{HR}\n  📖 HOUSE RULES\n{HR}")
            print("  1. Fib grid decides WHERE, astro decides HOW MUCH.")
            print("  2. NEUTRAL + size 1.0 = no trade.")
            print("  3. SHORT on card ≠ short market. Take profit, don't chase.")
            print("  4. Buy 0-bounce (62% OOS) or -1.272 (deep zone).")
            print("  5. Danger: Moon-Saturn exact (×0.6) / Grand Cross (×0.5) / U=S/P (×0.7).")
            print("  6. Gold: ignore calibrated stars (SPY-trained).")
            input(f"\n{C['dim']}Press ENTER...{C['reset']}")
        elif ch == "0":
            print("\n  👋  Good luck. Anchor at 23:00. See you tomorrow.")
            sys.exit(0)


if __name__ == "__main__":
    main()