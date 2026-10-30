"""How long does a flood peak take to travel from Hirakud and Tikarpara to Naraj? (warning lead time)

    python mahanadi/travel_time.py <discharge.csv> <out_dir>

Two estimates from the GloFAS v4 daily series, 1997-2025, June-October:
1. lag (days) that maximises the correlation of day-to-day flow changes upstream vs at Naraj;
2. for every annual flood peak at Naraj, days since the largest flow at the upstream point in the 6 days before.
Daily data only resolve whole days; the routed flow in GloFAS is a model, so these are planning numbers that the
CWC gauge records can sharpen.
"""
import json
import sys

import numpy as np
import pandas as pd

Q = pd.read_csv(sys.argv[1], index_col="date", parse_dates=True)
Q = Q[(Q.index.year <= 2025)]
mon = Q[Q.index.month.isin([6, 7, 8, 9, 10])]
out = {}
for up in ("hirakud_below", "tikarpara"):
    d_up, d_dn = Q[up].diff(), Q["naraj"].diff()
    corr = {}
    for lag in range(0, 6):
        x = d_up.shift(lag)[mon.index]
        corr[lag] = float(x.corr(d_dn[mon.index]))
    best = max(corr, key=corr.get)
    lags = []
    for yr, grp in Q.groupby(Q.index.year):
        g = grp["naraj"].dropna()
        if g.empty:
            continue
        t_peak = g.idxmax()
        window = Q[up][t_peak - pd.Timedelta(days=6):t_peak].dropna()
        if window.empty:
            continue
        lags.append((t_peak - window.idxmax()).days)
    out[up] = dict(corr_by_lag_days={k: round(v, 3) for k, v in corr.items()}, best_lag_days=best,
                   annual_peak_lag_days_median=float(np.median(lags)),
                   annual_peak_lag_days_iqr=[float(np.percentile(lags, 25)), float(np.percentile(lags, 75))],
                   years=len(lags), mean_flow_m3s=round(float(Q[up].mean())))
out["naraj_mean_flow_m3s"] = round(float(Q["naraj"].mean()))
json.dump(out, open(f"{sys.argv[2]}/travel_time.json", "w"), indent=1)
print(json.dumps(out, indent=1))
