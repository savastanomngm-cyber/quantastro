#!/usr/bin/env python3
"""Standalone backtest runner.

Modes:
  vanilla:   run_backtest.py --start ... --end ... --ticker SPY
  optimize:  run_backtest.py --start ... --end ... --ticker SPY --optimize
  signals:   run_backtest.py --start ... --end ... --ticker SPY --signals [--csv signals.csv]
             Dumps every astro signal + market returns as a CSV for inspection,
             further analysis, or feeding into an ML pipeline.
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="AstroQuant backtest — correlate astro signals with market returns",
    )
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--ticker", default="SPY", help="yfinance ticker (default: SPY)")

    # Mode flags (mutually exclusive-ish)
    parser.add_argument("--signals", action="store_true",
                        help="Export daily signal CSV (all astro columns + market returns)")
    parser.add_argument("--optimize", action="store_true",
                        help="Train/test split + optimized Bradley + confluence + Stellium vol")
    parser.add_argument("--csv", type=str, default=None,
                        help="Output path for CSV (with --signals)")

    # Optimization params
    parser.add_argument("--train-ratio", type=float, default=0.5,
                        help="Fraction for training (default: 0.5)")
    parser.add_argument("--lambda", type=float, default=0.01, dest="lambd",
                        help="Ridge regularization (default: 0.01)")

    # Output format
    parser.add_argument("--no-zscore", action="store_true", help="Skip Bradley decile analysis")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of summary")
    args = parser.parse_args()

    if args.signals:
        from astroquant.signals import compute_signals_with_returns, signals_to_csv

        # If optimize, learn weights first, then apply to signal export
        opt_weights = None
        if args.optimize:
            from astroquant.backtest import optimize_and_backtest
            opt_result = optimize_and_backtest(
                start=args.start, end=args.end, ticker=args.ticker,
                train_ratio=args.train_ratio, lambd=args.lambd,
            )
            if "error" in opt_result:
                print(f"Optimization error: {opt_result['error']}", file=sys.stderr)
                print("Falling back to unoptimized signals...")
            else:
                opt_weights = opt_result["optimization"]["weights"]
                print("# Optimized weights learned from training period")
                print(f"# In-sample R²: {opt_result['optimization']['r2']}")
                print(f"# Train days: {opt_result['optimization']['train_days']}")
                print(f"# Top 5 features:")
                for name, wt in opt_result["optimization"]["feature_importance"][:5]:
                    print(f"#   {name}: {wt:+.6f}")
                print()

        output = signals_to_csv(
            args.start, args.end, args.ticker,
            output_path=args.csv,
            optimized_weights=opt_weights,
        )
        print(output)

    elif args.optimize:
        from astroquant.backtest import optimize_and_backtest
        result = optimize_and_backtest(
            start=args.start, end=args.end, ticker=args.ticker,
            train_ratio=args.train_ratio, lambd=args.lambd,
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

    else:
        from astroquant.backtest import fetch_and_analyze
        result = fetch_and_analyze(
            start=args.start, end=args.end,
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