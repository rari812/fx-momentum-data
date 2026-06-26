# fx-momentum-data (Path B)

A GitHub Action fetches daily FX closes and commits them; the strategy chamber
reads them via raw URLs and ranks cross-sectional currency momentum on demand.

## Setup
1. Create a **public** repo. Add at the root:
   - `fetch_fx_data.py`
   - `.github/workflows/fetch-fx.yml`   ← the `fetch-fx.yml` file goes in this path
2. Repo → Settings → Actions → General → Workflow permissions → **Read and write**.
   (Skipping this silently breaks the `git push` step.)
3. Actions tab → `fetch-fx` → **Run workflow** (manual first run). Confirm a `data/`
   folder appears and `data/coverage.csv` shows `ok=True` for the majors.
4. Hand the chamber this base URL:
   `https://raw.githubusercontent.com/<user>/<repo>/main/data`

## Cadence
- Action: daily 22:00 UTC (after NY close), weekdays. Data is kept 6mo fresh.
- Ranking: run `momentum_rank.py --source <raw-base-url>` from the chamber when asked.

## Data contract
- `data/fx_daily.csv` — `date,ticker,close` (long)
- `data/coverage.csv` — `ticker,rows,first_date,last_date,days_stale,ok`
- `data/last_updated.txt` — ISO-8601 UTC

## Reliability mechanism
The fetch flags any series shorter than 60 bars or staler than 4 days (`ok=False`);
the ranker drops flagged tickers rather than sorting on bad data. That enforcement
is what makes the ranking trustworthy — without it the sort corrupts silently.
