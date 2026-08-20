import yfinance as yf
import pandas as pd

d = yf.download('GC=F', start='2026-08-16', end='2026-08-21', interval='1h', progress=False)
d.index = pd.to_datetime(d.index)
print("columns:", d.columns.tolist())
print("rows:", len(d))

# For each calendar day, min low and max high from hourly bars
for day in ['2026-08-17', '2026-08-18', '2026-08-19', '2026-08-20']:
    sub = d[[ts.strftime('%Y-%m-%d') == day for ts in d.index]]
    if len(sub):
        lo = float(sub['Low'].min())
        hi = float(sub['High'].max())
        op = float(sub['Open'].iloc[0])
        cl = float(sub['Close'].iloc[-1])
        n = len(sub)
        first = sub.index[0].strftime('%H:%M')
        last = sub.index[-1].strftime('%H:%M')
        print(f"{day}: n={n} first={first} last={last} O={op:.1f} H={hi:.1f} L={lo:.1f} C={cl:.1f}")
    else:
        print(f"{day}: no hourly bars")
