"""How much of a Naraj flood peak comes from Hirakud dam, and how much from the catchment below it.

    IMPACT_DIR=runs/_atlas/impact_r20 python mahanadi/watershed_share.py data/mahanadi_context/discharge.csv

GloFAS v4 daily flows just below Hirakud and at Naraj (Open-Meteo flood API, fetch_context.py). For every complete year
1997-2025 the flow below Hirakud on the day before the Naraj annual peak (one day = the travel time of travel_time.py)
is divided by the peak; the July-September means give the share of the ordinary monsoon flow.
Output: <IMPACT_DIR>/watershed_summary.json
"""
import json
import sys

import numpy as np
import pandas as pd

from impact_common import IMPACT

Q = pd.read_csv(sys.argv[1], index_col="date", parse_dates=True)
Q = Q[(Q.index.year >= 1984) & (Q.index.year <= 2025)].dropna(subset=["naraj"])
rows = []
for y, g in Q.groupby(Q.index.year):
    if g["naraj"].notna().sum() < 300:
        continue
    d = g["naraj"].idxmax()
    prev = d - pd.Timedelta(days=1)
    hb = Q.loc[prev, "hirakud_below"] if prev in Q.index else np.nan
    rows.append(dict(year=y, naraj_peak=g["naraj"].max(), hirakud_prev_day=hb, share=hb / g["naraj"].max()))
R = pd.DataFrame(rows)
m = Q[Q.index.month.isin([7, 8, 9])]
out = dict(years=int(len(R)), median_share_hirakud_of_naraj_peak=round(float(R.share.median()), 2),
           iqr=[round(float(x), 2) for x in R.share.quantile([0.25, 0.75])],
           top5=R.sort_values("naraj_peak", ascending=False).head(5).round(2).to_dict("records"),
           jul_sep_mean_naraj=round(float(m.naraj.mean())), jul_sep_mean_hirakud=round(float(m.hirakud_below.mean())),
           jul_sep_share=round(float(m.hirakud_below.mean() / m.naraj.mean()), 2))
json.dump(out, open(f"{IMPACT}/watershed_summary.json", "w"), indent=1)
print(json.dumps(out, indent=1))
