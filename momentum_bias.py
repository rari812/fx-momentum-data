#!/usr/bin/env python3
"""
FX directional-bias compass with recent-move confirmation.
50d return = higher-timeframe bias. 10d return = is price currently confirming it?
  ALIGNED -> 10d agrees with 50d: bias is live, hunt the zone in that direction.
  DIVERGE -> 10d contradicts 50d: move is fading, stand aside / wait for re-align.
Per-pair bias for zone entries. NOT a portfolio.

Default source is the live repo, so no args needed:
  python momentum_bias.py
Override:
  python momentum_bias.py --source ./data
"""
import argparse, io
import numpy as np, pandas as pd, urllib.request

DEFAULT_SOURCE = "https://raw.githubusercontent.com/rari812/fx-momentum-data/main/data"
LB_LONG, LB_SHORT = 50, 10
LEG = {"EURUSD=X":("EUR",+1),"GBPUSD=X":("GBP",+1),"AUDUSD=X":("AUD",+1),
       "NZDUSD=X":("NZD",+1),"USDJPY=X":("JPY",-1),"USDCHF=X":("CHF",-1),
       "USDCAD=X":("CAD",-1)}
PRIORITY = ["EUR","GBP","AUD","NZD","USD","CAD","CHF","JPY"]

def load(src,name):
    if src.startswith("http"):
        with urllib.request.urlopen(f"{src}/{name}") as r: return r.read().decode()
    with open(f"{src}/{name}") as f: return f.read()

def legret(col,n): return np.log(col.iloc[-1]/col.iloc[-(n+1)])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--source",default=DEFAULT_SOURCE); a=ap.parse_args()
    prices=pd.read_csv(io.StringIO(load(a.source,"fx_daily.csv")))
    cov=pd.read_csv(io.StringIO(load(a.source,"coverage.csv")))
    bad=set(cov.loc[~cov["ok"].astype(bool),"ticker"])
    prices["date"]=pd.to_datetime(prices["date"])
    wide=prices.pivot(index="date",columns="ticker",values="close").sort_index()
    r50,r10={"USD":0.0},{"USD":0.0}
    for t,(c,s) in LEG.items():
        if t in bad or t not in wide.columns: continue
        col=wide[t].dropna()
        if len(col)<=LB_LONG: continue
        r50[c]=s*legret(col,LB_LONG); r10[c]=s*legret(col,LB_SHORT)
    ccys=[c for c in PRIORITY if c in r50]
    rows=[]
    for i,b in enumerate(ccys):
        for q in ccys[i+1:]:
            x50=r50[b]-r50[q]; x10=r10[b]-r10[q]
            p50=(np.exp(x50)-1)*100; p10=(np.exp(x10)-1)*100
            bias="LONG " if x50>0 else "SHORT"
            status="ALIGNED" if np.sign(x10)==np.sign(x50) else "DIVERGE"
            hunt="demand / lows " if x50>0 else "supply / highs"
            rows.append((f"{b}{q}",p50,p10,bias,status,hunt))
    df=pd.DataFrame(rows,columns=["Pair","R50","R10","Bias","Status","Hunt"]).sort_values("R50",ascending=False)
    last=load(a.source,"last_updated.txt").strip()
    print(f"\n=== 50d BIAS + 10d CONFIRMATION — G10 majors ===  (data: {last})")
    print(f"{'Pair':<8}{'50d':>8}{'10d':>8}   {'Bias':<6}{'Status':<9}Hunt")
    for _,x in df.iterrows():
        mark="" if x.Status=="ALIGNED" else "  <- wait"
        print(f"{x.Pair:<8}{x.R50:>+7.2f}%{x.R10:>+7.2f}%   {x.Bias:<6}{x.Status:<9}{x.Hunt}{mark}")
    n=(df.Status=="DIVERGE").sum()
    print(f"\n{n}/{len(df)} DIVERGE (50d bias not confirmed by last 10d -> stand aside).")

if __name__=="__main__": main()
