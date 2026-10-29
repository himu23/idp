"""Construction technology and management: when to build, how much earthwork, what to install, in what order.

    python mahanadi/cm_plan.py <discharge.csv> <ibtracs_NI.csv> <out_fig_dir>   (after the impact scripts and impact_depth.py)

1. Work windows. Month by month: share of days with Naraj flow above the 2-year flood (GloFAS 1984-2025), mean
   flooded share of the radar passes (atlas), and Bay of Bengal systems within 300 km (IBTrACS 1980-2025). Months
   with no flood days, low flooding and few storms are the windows for embankment repair, road raising and
   installation.
2. Raising the critical links. For the 10 links of the 25-year flood (impact_transport.py): raise height = 90th
   percentile flood depth around the flooded section (impact_depth.py) + 0.6 m freeboard (a common rural-road
   value; check IRC SP:20 / IRC:37); embankment of crest width 3.75 m (single lane) or 7.5 m (trunk / primary) and
   side slopes 2H:1V; volume = (b h + 2 h^2) x flooded length. Cost at an ASSUMED Rs 350/m3 for compacted earthwork
   (replace with the Odisha schedule of rates). A raise above 3 m is not a road embankment: such a link needs a bridge
   or a vented causeway (and its DEM depth a site check first), so it is listed but kept out of the earthwork total.
3. Deployment quantities: sirens for 50 % and 80 % coverage of the exposed people at 1.5 km (impact_siting.py),
   river-sensor sites, with installation effort (assumed 1 crew-day per siren, 2 per bridge sensor incl. the
   cross-section survey). Unit costs are left to ClimMaTech's quotation.
4. Schedule (Gantt) for a deployment before the next monsoon, inside the work window.
Outputs: runs/_atlas/impact/cm_plan.json, link_raising.csv, boq.csv; figures construction_windows.png, gantt.png
"""
import json
import os
import sys

import matplotlib
import numpy as np
import pandas as pd
from pyproj import Transformer

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from impact_common import ATLAS, IMPACT, Grid, dump, read  # noqa: E402

FIG = sys.argv[3]
os.makedirs(FIG, exist_ok=True)
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 160,
                     "savefig.bbox": "tight"})
S = json.load(open(f"{ATLAS}/atlas_summary.json"))
RP = {int(k): v for k, v in S["gumbel"]["return_period_m3s"].items()}
out = {}

# 1. work windows
Q = pd.read_csv(sys.argv[1], index_col="date", parse_dates=True)["naraj"]
Q = Q[Q.index.year <= 2025]
p_flood = Q.groupby(Q.index.month).apply(lambda s: float((s >= RP[2]).mean()))
q_mean = Q.groupby(Q.index.month).mean()
passes = pd.read_csv(f"{ATLAS}/atlas_passes.csv", parse_dates=["date"])
fl_month = passes.groupby(passes.date.dt.month).flood_frac.mean()
tr = pd.read_csv(sys.argv[2], skiprows=[1], low_memory=False, usecols=["SID", "SEASON", "ISO_TIME", "LAT", "LON"])
tr = tr[pd.to_numeric(tr.SEASON, errors="coerce") >= 1980]
lat, lon = pd.to_numeric(tr.LAT, errors="coerce"), pd.to_numeric(tr.LON, errors="coerce")
d = 6371 * 2 * np.arcsin(np.sqrt(np.sin(np.radians(20.45 - lat) / 2) ** 2 + np.cos(np.radians(lat)) * np.cos(np.radians(20.45))
                                 * np.sin(np.radians(86.12 - lon) / 2) ** 2))
near = tr[d <= 300]
storms = near.groupby("SID").ISO_TIME.min().pipe(pd.to_datetime).dt.month.value_counts().reindex(range(1, 13), fill_value=0)
yrs = 2025 - 1980 + 1
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
tab = pd.DataFrame(dict(month=months, mean_flow_m3s=q_mean.reindex(range(1, 13)).round().values,
                        share_days_above_2yr_flood=p_flood.reindex(range(1, 13)).round(3).values,
                        storms_per_year_within_300km=(storms / yrs).round(2).values,
                        mean_flooded_share_on_radar=fl_month.reindex(range(1, 13)).round(3).values))
ok = (tab.share_days_above_2yr_flood == 0) & (tab.storms_per_year_within_300km < 0.1)
tab["work_window"] = np.where(ok, "yes", "no")
out["work_window_months"] = tab.month[ok].tolist()
fig, axs = plt.subplots(1, 3, figsize=(11, 3), sharex=True)
x = np.arange(12)
axs[0].bar(x, tab.mean_flow_m3s / 1000, color="#3b6ea8")
axs[0].set_title("Mean Naraj flow (1000 m³/s)", loc="left", fontsize=9)
axs[1].bar(x, tab.share_days_above_2yr_flood * 100, color="#d95f02")
axs[1].set_title("Days above the 2-year flood (%)", loc="left", fontsize=9)
axs[2].bar(x, tab.storms_per_year_within_300km, color="#7a2e8e")
axs[2].set_title("Bay of Bengal systems within 300 km per year", loc="left", fontsize=9)
for a_ in axs:
    a_.set_xticks(x, [m[0] for m in months])
    for i in np.where(ok)[0]:
        a_.axvspan(i - 0.5, i + 0.5, color="#e8f4fc", zorder=0)
fig.suptitle("Construction windows (shaded): no flood days and few storms", x=0.01, ha="left", fontsize=10)
fig.savefig(f"{FIG}/construction_windows.png")
plt.close(fig)

# 2. raising the critical links
g = Grid()
to_xy = Transformer.from_crs(4326, g.crs, always_xy=True)
cl = pd.read_csv(f"{IMPACT}/critical_links.csv")
cl = cl[cl.scenario == "T25"].head(10).copy()
try:
    dd = read(f"{IMPACT}/depth_T25.tif").astype(np.float64)
    depth = np.where(dd == 255, np.nan, dd / 10)
except Exception:
    depth = None
RATE = 350.0
MAX_RAISE = 3.0  # m; higher than this, cross-drainage structures replace an embankment
rows = []
for _, r in cl.iterrows():
    x, y = to_xy.transform(r.lon, r.lat)
    rr, cc, inside = g.rc(np.array([x]), np.array([y]))
    win = depth[max(rr[0] - 5, 0):rr[0] + 6, max(cc[0] - 5, 0):cc[0] + 6] if depth is not None and inside[0] else np.array([np.nan])
    dep = float(np.nanpercentile(win, 90)) if np.isfinite(win).any() else 0.5
    h = round(dep + 0.6, 2)
    b = 7.5 if str(r.highway).startswith(("trunk", "primary")) else 3.75
    area = b * h + 2 * h * h
    vol = area * r.flooded_km * 1000
    emb = h <= MAX_RAISE
    rows.append(dict(rank=int(r["rank"]), road=r.road if isinstance(r.road, str) else "(unnamed)", highway=r.highway,
                     flooded_km=r.flooded_km, depth_p90_m=round(dep, 2), raise_m=h, crest_m=b,
                     design="embankment raise" if emb else "bridge or vented causeway",
                     earthwork_m3=round(vol) if emb else 0, cost_lakh_rs_at_350_per_m3=round(vol * RATE / 1e5, 1) if emb else 0.0,
                     earthwork_m3_as_embankment=round(vol), people_routed=int(r.people_routed), lat=r.lat, lon=r.lon))
lr = pd.DataFrame(rows)
lr.to_csv(f"{IMPACT}/link_raising.csv", index=False)
emb = lr[lr.design == "embankment raise"] if len(lr) else lr
out["link_raising"] = dict(links=len(lr), total_km=round(float(lr.flooded_km.sum()), 2) if len(lr) else 0,
                           links_by_embankment=len(emb), embankment_km=round(float(emb.flooded_km.sum()), 2) if len(emb) else 0,
                           earthwork_m3=int(emb.earthwork_m3.sum()) if len(emb) else 0,
                           cost_crore_rs_at_350_per_m3=round(float(emb.earthwork_m3.sum() * RATE / 1e7), 2) if len(emb) else 0,
                           max_raise_for_embankment_m=MAX_RAISE,
                           links_needing_structure=[dict(rank=int(x["rank"]), flooded_km=float(x.flooded_km), raise_m=float(x.raise_m),
                                                         lat=float(x.lat), lon=float(x.lon))
                                                    for _, x in lr[lr.design != "embankment raise"].iterrows()] if len(lr) else [],
                           earthwork_m3_if_all_by_embankment=int(lr.earthwork_m3_as_embankment.sum()) if len(lr) else 0,
                           # a person whose route crosses two links is counted twice in the sum, so report the range per link
                           people_routed_per_link=[int(lr.people_routed.min()), int(lr.people_routed.max())] if len(lr) else [0, 0],
                           hospital_routes_summed_over_links=int(lr.people_routed.sum()) if len(lr) else 0)

# 3. deployment quantities
curve = pd.read_csv(f"{IMPACT}/siren_coverage_curve.csv")
c15 = curve[curve.radius_m == 1500]
n50 = int(c15[c15.share >= 0.5].sirens.min()) if (c15.share >= 0.5).any() else None
n80 = int(c15[c15.share >= 0.8].sirens.min()) if (c15.share >= 0.8).any() else None
nsen = len(pd.read_csv(f"{IMPACT}/sensor_sites.csv"))
nsir = n50 or int(c15.sirens.max())
share_nsir = float(c15[c15.sirens == nsir].share.max())
boq = pd.DataFrame([
    dict(item="Solar siren unit with controller (Rakshak-type), mast and foundation", unit="site", qty=nsir,
         basis=f"{nsir} sirens cover {share_nsir:.0%} of the exposed people at a 1.5 km audible range (impact_siting.py)",
         crew_days=nsir * 1),
    dict(item="Non-contact radar level + surface-velocity station (Pravaah-type) on bridge, with logger and telemetry",
         unit="site", qty=nsen, basis="one per main distributary (impact_siting.py)", crew_days=nsen * 2),
    dict(item="Cross-section and bed-material survey at each sensor bridge", unit="site", qty=nsen,
         basis="needed to turn level + surface velocity into discharge", crew_days=nsen * 1),
    dict(item="Community training and siren drills", unit="village", qty=nsir, basis="one session per siren site", crew_days=nsir * 0.5)])
boq.to_csv(f"{IMPACT}/boq.csv", index=False)
out["deployment"] = dict(sirens=nsir, siren_share_covered_1500m=round(share_nsir, 3), sirens_for_50pct=n50, sirens_for_80pct=n80,
                         sensor_sites=nsen, crew_days=float(boq.crew_days.sum()))

# 4. schedule (months from Nov 2026)
tasks = [("Approvals: WRD, district, panchayats", 0, 1.5), ("Site surveys (signal, mounting, cross-sections)", 0.5, 1.5),
         ("Procurement and fabrication", 1, 2.5), ("Installation in the work window", 2, 3.5),
         ("Calibration, drills, handover", 4.5, 1.5), ("Refit trigger map with CWC flows", 2, 2),
         ("Monsoon operation and verification", 7, 5)]
fig, ax = plt.subplots(figsize=(9, 3))
for i, (name, s0, dur) in enumerate(tasks):
    ax.barh(i, dur, left=s0, color="#0c3c6c" if "Monsoon" not in name else "#0c9ce4", height=0.5)
    ax.text(s0 + dur + 0.1, i, name, va="center", fontsize=8)
mlab = ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"]
ax.set_xticks(range(13), mlab)
ax.set_yticks([])
ax.set_xlim(0, 14.5)
ax.invert_yaxis()
for i, m in enumerate(mlab[:12]):
    if m in out["work_window_months"]:
        ax.axvspan(i, i + 1, color="#e8f4fc", zorder=0)
ax.set_title("Deployment schedule, Nov 2026 – Nov 2027 (shaded: construction window)", loc="left", fontsize=10)
fig.savefig(f"{FIG}/gantt.png")
plt.close(fig)
out["work_windows_table"] = tab.to_dict("records")
dump(out, f"{IMPACT}/cm_plan.json")
print(tab.to_string(index=False))
print(lr.to_string(index=False))
print(boq.to_string(index=False))
print(json.dumps({k: v for k, v in out.items() if k != "work_windows_table"}, indent=1))
print("CM_DONE")
