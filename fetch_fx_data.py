#!/usr/bin/env python3
"""
Path B FX fetch — runs on a GitHub Actions runner (open internet; reaches Yahoo).
Pulls 6mo daily closes for the momentum-ranking universe, validates coverage and
freshness, and commits data + a coverage report to the repo. The chamber analysis
script reads the committed files via raw.githubusercontent.com.

DATA CONTRACT (must stay in sync with momentum_rank.py):
  data/fx_daily.csv     long format: date,ticker,close
  data/coverage.csv     ticker,rows,first_date,last_date,days_stale,ok
  data/last_updated.txt ISO-8601 UTC timestamp
"""
import os, sys, datetime as dt
import pandas as pd
import yfinance as yf

# USD legs only — cleanest free data. Currency strength is built from these in
# momentum_rank.py via equal-weight-basket decomposition, so all crosses aren't needed.
TICKERS = [
    "EURUSD=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X",   # USD-quote majors
    "USDJPY=X", "USDCHF=X", "USDCAD=X",               # USD-base majors
    "USDNOK=X", "USDSEK=X",                            # Scandi
    "USDMXN=X", "USDZAR=X", "USDTRY=X",               # liquid EM
]

PERIOD = "6mo"        # need >=50 trading days; 6mo gives margin
MIN_ROWS = 60         # reject series too short to compute a 50d return safely
MAX_STALE_DAYS = 4    # tolerate a long weekend; flag anything older

OUTDIR = "data"


def fetch_one(ticker):
    h = yf.Ticker(ticker).history(period=PERIOD, interval="1d", auto_adjust=False)
    if h is None or h.empty:
        return None
    s = h["Close"].dropna()
    idx = pd.to_datetime(s.index)
    if idx.tz is not None:                       # normalise tz-aware index safely
        idx = idx.tz_convert("UTC").tz_localize(None)
    s.index = idx.normalize()
    return s


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    today = dt.date.today()
    rows, cov, failed = [], [], []

    for t in TICKERS:
        try:
            s = fetch_one(t)
        except Exception as e:
            s = None
            print(f"[warn] {t}: {e}", file=sys.stderr)
        if s is None or s.empty:
            failed.append(t)
            cov.append((t, 0, "", "", "", False))
            continue
        first, last = s.index.min().date(), s.index.max().date()
        stale = (today - last).days
        ok = (len(s) >= MIN_ROWS) and (stale <= MAX_STALE_DAYS)
        cov.append((t, len(s), str(first), str(last), stale, ok))
        for d, v in s.items():
            rows.append((d.date().isoformat(), t, float(v)))

    if not rows:
        print("[fatal] no data fetched for any ticker", file=sys.stderr)
        sys.exit(1)

    pd.DataFrame(rows, columns=["date", "ticker", "close"]) \
        .to_csv(os.path.join(OUTDIR, "fx_daily.csv"), index=False)

    covdf = pd.DataFrame(
        cov, columns=["ticker", "rows", "first_date", "last_date", "days_stale", "ok"])
    covdf.to_csv(os.path.join(OUTDIR, "coverage.csv"), index=False)

    with open(os.path.join(OUTDIR, "last_updated.txt"), "w") as f:
        f.write(dt.datetime.utcnow().isoformat() + "Z\n")

    n_ok = int(covdf["ok"].sum())
    print(f"fetched {len(TICKERS)} tickers | ok={n_ok} | failed={len(failed)} {failed}")
    # Partial coverage is not fatal; the analysis script drops flagged tickers.


if __name__ == "__main__":
    main()
