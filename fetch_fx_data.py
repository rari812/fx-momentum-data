#!/usr/bin/env python3
"""
Path B FX fetch (MAJORS ONLY) — runs on a GitHub Actions runner.
Pulls 6mo daily closes for the 7 USD legs needed to build the 28 G10-major
crosses. Exotics (ZAR/MXN/TRY) and Scandi (NOK/SEK) dropped — untradeable /
spread-punitive on BlackBull. Validates coverage/freshness, commits data.

DATA CONTRACT (sync with momentum_rank.py):
  data/fx_daily.csv     date,ticker,close
  data/coverage.csv     ticker,rows,first_date,last_date,days_stale,ok
  data/last_updated.txt ISO-8601 UTC
"""
import os, sys, datetime as dt
import pandas as pd
import yfinance as yf

# 7 USD legs -> all 28 major crosses are derivable downstream.
TICKERS = [
    "EURUSD=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X",
    "USDJPY=X", "USDCHF=X", "USDCAD=X",
]

PERIOD = "6mo"
MIN_ROWS = 60
MAX_STALE_DAYS = 4
OUTDIR = "data"


def fetch_one(ticker):
    h = yf.Ticker(ticker).history(period=PERIOD, interval="1d", auto_adjust=False)
    if h is None or h.empty:
        return None
    s = h["Close"].dropna()
    idx = pd.to_datetime(s.index)
    if idx.tz is not None:
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
        print("[fatal] no data fetched", file=sys.stderr)
        sys.exit(1)
    pd.DataFrame(rows, columns=["date", "ticker", "close"]) \
        .to_csv(os.path.join(OUTDIR, "fx_daily.csv"), index=False)
    pd.DataFrame(cov, columns=["ticker","rows","first_date","last_date","days_stale","ok"]) \
        .to_csv(os.path.join(OUTDIR, "coverage.csv"), index=False)
    with open(os.path.join(OUTDIR, "last_updated.txt"), "w") as f:
        f.write(dt.datetime.utcnow().isoformat() + "Z\n")
    print(f"fetched {len(TICKERS)} | failed={len(failed)} {failed}")


if __name__ == "__main__":
    main()
