"""Ocean side of delta flooding: Bay of Bengal cyclones and depressions, and what drove each large flood.

    python mahanadi/ocean_cyclones.py <ibtracs_NI.csv> <rain.csv> <discharge.csv>      (after atlas_build.py)

IBTrACS v04r01 North Indian tracks. A system "affects the delta" when its centre passes within 300 km of the box
centre (20.45 N, 86.12 E). For each such system since 2016: closest approach, intensity there (WMO/IMD wind), the
largest flood seen on a radar pass in the 7 days after, the rain over the delta and the Naraj flow then.
Every one of the 20 largest flood passes is then labelled by its drivers: river (Naraj flow >= monsoon 90th
percentile), rain (rain predictor >= monsoon 90th percentile), cyclone/depression (a system within 300 km in the
previous 7 days). Storm surge and high tide also slow the drainage of the lower delta; the study box ends ~25 km
inland of Paradip and no tide record is used here, which is stated as a limit.
Outputs in runs/_atlas/impact: cyclones_near_delta.csv, flood_drivers.csv, ocean_summary.json
"""
import json
import sys

import numpy as np
import pandas as pd

from impact_common import ATLAS, IMPACT, dump

LAT0, LON0, R_KM = 20.45, 86.12, 300
tr = pd.read_csv(sys.argv[1], skiprows=[1], low_memory=False,
                 usecols=["SID", "SEASON", "NAME", "ISO_TIME", "NATURE", "LAT", "LON", "WMO_WIND", "USA_WIND", "NEWDELHI_WIND"])
tr = tr[tr.SEASON.astype(int) >= 2016].copy()
for c in ("LAT", "LON", "WMO_WIND", "USA_WIND", "NEWDELHI_WIND"):
    tr[c] = pd.to_numeric(tr[c], errors="coerce")
tr["t"] = pd.to_datetime(tr.ISO_TIME)
la1, lo1, la2, lo2 = map(np.radians, (tr.LAT, tr.LON, LAT0, LON0))
tr["dist_km"] = 6371 * 2 * np.arcsin(np.sqrt(np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2))
tr["wind_kt"] = tr.NEWDELHI_WIND.fillna(tr.WMO_WIND).fillna(tr.USA_WIND)
near = tr[tr.dist_km <= R_KM]
rain = pd.read_csv(sys.argv[2], index_col="date", parse_dates=True)["rain_mm"]
Q = pd.read_csv(sys.argv[3], index_col="date", parse_dates=True)["naraj"]
S = json.load(open(f"{ATLAS}/atlas_summary.json"))
passes = pd.read_csv(f"{ATLAS}/atlas_passes.csv", parse_dates=["date"])
rp = S.get("rain_predictor", "R_7d")
win = int("".join(ch for ch in rp if ch.isdigit()) or 7)
R = rain.rolling(win).sum()
rows = []
for sid, g in near.groupby("SID"):
    c = g.loc[g.dist_km.idxmin()]
    t0 = c.t.normalize()
    after = passes[(passes.date >= t0) & (passes.date <= t0 + pd.Timedelta(days=7))]
    big = after.loc[after.flood_km2.idxmax()] if len(after) else None
    rows.append(dict(name=str(c.NAME).title(), sid=sid, closest_date=str(t0.date()), min_dist_km=round(c.dist_km),
                     wind_kt_at_closest=None if pd.isna(c.wind_kt) else int(c.wind_kt),
                     max_wind_kt_near=None if g.wind_kt.isna().all() else int(g.wind_kt.max()),
                     rain_week_mm=round(float(rain[t0 - pd.Timedelta(days=1):t0 + pd.Timedelta(days=5)].sum())),
                     naraj_max_week_m3s=round(float(Q[t0:t0 + pd.Timedelta(days=7)].max())),
                     passes_in_week=int(len(after)),
                     max_flood_km2_on_a_pass=None if big is None else round(float(big.flood_km2), 1),
                     pass_date=None if big is None else str(big.date.date())))
cy = pd.DataFrame(rows).sort_values("closest_date")
cy.to_csv(f"{IMPACT}/cyclones_near_delta.csv", index=False)

q90 = S["validation"]["high_flow_passes"]["q90_threshold_m3s"]
r90 = S["validation"].get("high_rain_passes", {}).get("r90_threshold_mm", float(R[R.index.month.isin(range(6, 12))].quantile(0.9)))
top = passes.sort_values("flood_frac", ascending=False).head(20).copy()
drivers = []
for _, p in top.iterrows():
    d = p.date.normalize()
    qv, rv = float(p.q), float(R.get(d, np.nan))
    sysn = near[(near.t.dt.normalize() <= d) & (near.t.dt.normalize() >= d - pd.Timedelta(days=7))]
    tags = [t for t, ok in (("river", qv >= q90 - 0.5), ("rain", rv >= r90 - 0.05), ("cyclone/depression", len(sysn) > 0)) if ok]
    drivers.append(dict(date=str(d.date()), flood_km2=round(float(p.flood_km2), 1), flood_share_of_observed_land=round(float(p.flood_frac), 3),
                        naraj_m3s=round(qv), rain_mm=round(rv), system=", ".join(sorted(set(str(x).title() for x in sysn.NAME))) or "",
                        drivers=" + ".join(tags) or "none above the 90th percentiles"))
dr = pd.DataFrame(drivers)
dr.to_csv(f"{IMPACT}/flood_drivers.csv", index=False)
counts = {k: int(dr.drivers.str.contains(k, regex=False).sum()) for k in ("river", "rain", "cyclone/depression")}
dump(dict(systems_within_300km_since_2016=len(cy), named=sorted(set(cy.name) - {"Not_Named", "Not Named"}),
          top20_flood_passes_driver_counts=counts, q90_m3s=q90, r90_mm=r90, rain_predictor=rp), f"{IMPACT}/ocean_summary.json")
print(cy.to_string(index=False))
print(dr.to_string(index=False))
print(counts)
print("OCEAN_DONE")
