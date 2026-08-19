#!/usr/bin/env python3
"""Standalone backtest runner: fetch market data + compute astro signals + analyze.

Two modes:
  1. vanilla:  run_backtest.py --start ... --end ... --ticker SPY
     Runs the basic backtest with theoretical Bradley weights.

  2. optimize: run_backtest.py --start ... --end ... --ticker SPY --optimize
     Splits data into train/test, learns optimal Bradley weights from
     the training period, then evaluates all signals (optimized Bradley,
     confluence score, Stellium volatility) on the test period.
"""

import argparse
import sys

from astroquant.backtest import fetch_and_analyze


def main():
    parser = argparse.ArgumentParser(
        description="AstroQuant backtest — correlate astro signals with market returns",
    )
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--ticker", default="SPY", help="yfinance ticker (default: SPY)")
    parser.add_argument("--optimize", action="store_true",
                        help="Train/test split + optimized Bradley + confluence + Stellium vol")
    parser.add_argument("--train-ratio", type=float, default=0.5,
                        help="Fraction for training (default: 0.5)")
    parser.add_argument("--lambda", type=float, default=0.01, dest="lambd",
                        help="Ridge regularization (default: 0.01)")
    parser.add_argument("--no-zscore", action="store_true", help="Skip Bradley decile analysis")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of summary")
    args = parser.parse_args()

    if args.optimize:
        from astroquant.backtest import optimize_and_backtest
        result = optimize_and_backtest(
            start=args.start,
            end=args.end,
            ticker=args.ticker,
            train_ratio=args.train_ratio,
            lambd=args.lambd,
        )
    else:
        result = fetch_and_analyze(
            start=args.start,
            end=args.end,
            ticker=args.ticker,
            include_zscore=not args.no_zscore,
        )

    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        import json as _json
        out = {k: v for k, v in result.items()
               if k not in ("signal_df",) and not hasattr(v, "to_dict")}
        print(_json.dumps(out, indent=2, default=str))
    else:
        print(result["summary"])


if __name__ == "__main__":
    main()