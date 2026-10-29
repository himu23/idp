"""Forecast discharge at Naraj -> expected flooded land, settlements to warn and roads under water.

    python mahanadi/forecast_to_impact.py --q 24000 [--out bulletin_dir] [--lead "48 h"]
    python mahanadi/forecast_to_impact.py --lakh-cusec 8.5

The operational step this project adds to a point forecast (ClimMaTech forecasts level/flow 30 min to 48 h
ahead; CWC/OSDMA bulletins give Naraj flow in lakh cusec). Uses the atlas trigger-discharge map (pixel floods when
the Naraj flow reaches its trigger) and the impact layers; runs in a few seconds on a laptop.
Writes:
  flood_<q>.tif                 expected flooded land (1) on the 20 m grid
  settlements_<q>.geojson       settlements with >= 10 % of people on flooded land: name, people, share, location
  bulletin_<q>.json / .txt      summary numbers and a plain-text bulletin
  bulletin_<q>.cap.xml          the same as a CAP 1.2 alert (one area circle per settlement), as the Rakshak
                                Control Centre accepts alerts from other systems in CAP
Above the largest flow in the radar record the map cannot grow further and is marked as a lower bound.
"""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage

from impact_common import ATLAS, CTX, IMPACT, PIX_KM2, Grid, line_samples, osm, read

ap = argparse.ArgumentParser()
ap.add_argument("--q", type=float, help="forecast discharge at Naraj, m3/s")
ap.add_argument("--lakh-cusec", type=float, help="forecast discharge at Naraj, lakh cusec (1 lakh cusec = 2831.7 m3/s)")
ap.add_argument("--rain", type=float, help="forecast rain over the delta in mm (same window as the atlas rain predictor);"
                                       " switches to analog maps: land flooded on >= half of the 7 most similar past passes")
ap.add_argument("--lead", default="", help="forecast lead time, for the bulletin text")
ap.add_argument("--out", default=os.path.join(IMPACT, "bulletins"))
ap.add_argument("--alert-km", type=float, default=1.5, help="radius of each settlement's CAP alert circle (siren range)")
a = ap.parse_args()
q = a.q if a.q else a.lakh_cusec * 2831.7
os.makedirs(a.out, exist_ok=True)
g = Grid()
theta = read(f"{ATLAS}/trigger_discharge.tif")
normal = read(f"{ATLAS}/normal_water_latest.tif").astype(bool)
S = json.load(open(f"{ATLAS}/atlas_summary.json"))
flood = np.isfinite(theta) & (theta <= q) & ~normal
lower_bound = q > S["largest_observed_predictor_m3s"]
method = "trigger-discharge map, river flow only"
if a.rain is not None:
    lib = np.load(f"{ATLAS}/flood_library.npz", allow_pickle=True)  # our own file; pass names are stored as objects
    H_, W_ = (int(v) for v in lib["shape"])
    qs, rs = lib["q"], lib["r"]
    d = ((np.searchsorted(np.sort(qs), qs) - np.searchsorted(np.sort(qs), q)) / len(qs)) ** 2 +         ((np.searchsorted(np.sort(rs), rs) - np.searchsorted(np.sort(rs), a.rain)) / len(rs)) ** 2
    idx = np.argsort(d, kind="stable")[:7]
    fl_lib, vl_lib = lib["fl"], lib["vl"]
    f = sum(np.unpackbits(fl_lib[i])[:H_ * W_].reshape(H_, W_).astype(np.int16) for i in idx)
    v = sum(np.unpackbits(vl_lib[i])[:H_ * W_].reshape(H_, W_).astype(np.int16) for i in idx)
    flood = (v >= 3) & (2 * f >= v) & ~normal
    days = ", ".join(sorted(str(lib["names"][i])[3:11] for i in idx))
    method = f"analog maps on river flow and {a.rain:.0f} mm of 7-day rain; similar past passes: {days}"
    lower_bound = False

pop = np.nan_to_num(read(f"{CTX}/grid20_pop.tif").astype(np.float64))
lab = read(f"{IMPACT}/settlement_labels.tif")
st = pd.read_csv(f"{IMPACT}/settlements.csv")
share = ndimage.sum(pop * flood, lab, st.settlement.values) / np.maximum(st["pop"].values, 1)
st["share"] = share
hit = st[st.share >= 0.10].assign(people=lambda d: d["pop"] * d.share).sort_values("people", ascending=False)

roads = osm("roads", g.crs)
br = (roads["bridge"].notna() & (roads["bridge"] != "no")).values
idx, x, y, ln = line_samples(roads.geometry.values, 10.0)
wet = g.sample(flood, x, y, False) & ~br[idx]
cls = roads["highway"].values[idx]
main = np.isin(cls, ["trunk", "primary", "secondary", "tertiary", "trunk_link", "primary_link", "secondary_link"])
named = pd.Series(ln[wet & main]).groupby(roads["ref"].fillna(roads["name"]).values[idx][wet & main]).sum().sort_values(ascending=False)

tag = f"{q:.0f}" + (f"_rain{a.rain:.0f}" if a.rain is not None else "")
p = dict(g.profile, dtype="uint8", count=1, nodata=None, compress="deflate")
with rasterio.open(f"{a.out}/flood_{tag}.tif", "w", **p) as dst:
    dst.write(flood.astype(np.uint8)[None])
feats = [dict(type="Feature", geometry=dict(type="Point", coordinates=[round(r.lon, 5), round(r.lat, 5)]),
              properties=dict(name=r["name"], population=int(r["pop"]), share_flooded=round(float(r.share), 2),
                              people_on_flooded_land=int(r.people)))
         for _, r in hit.iterrows()]
json.dump(dict(type="FeatureCollection", features=feats), open(f"{a.out}/settlements_{tag}.geojson", "w"))
summary = dict(naraj_discharge_m3s=round(q), naraj_discharge_lakh_cusec=round(q / 2831.7, 2), lead_time=a.lead,
               rain_mm=a.rain, method=method,
               lower_bound=bool(lower_bound), flooded_land_km2=round(float(flood.sum() * PIX_KM2), 1),
               people_on_flooded_land=round(float(pop[flood].sum())), settlements_to_warn=len(hit),  # rounded like impact_exposure.py
               main_road_km_under_water=round(float(ln[wet & main].sum() / 1000), 1),
               all_road_km_under_water=round(float(ln[wet].sum() / 1000), 1),
               main_roads_affected={str(k): round(v / 1000, 1) for k, v in named.items() if v >= 300},
               model=dict(atlas_passes=S["n_passes"], predictor=S["predictor"],
                          held_out_high_flow_iou=S["validation"]["high_flow_passes"]["model"]["iou"]))
json.dump(summary, open(f"{a.out}/bulletin_{tag}.json", "w"), indent=1)
PRED = {"Q_same_day": "daily flow", "Q_prev_day": "previous day's flow", "Q_max_3d": "highest daily flow over 3 days",
        "Q_max_5d": "highest daily flow over 5 days", "Q_max_7d": "highest daily flow over 7 days"}.get(S["predictor"], "flow")
lines = [f"MAHANADI DELTA - EXPECTED FLOODING FOR A NARAJ FLOW OF {q:,.0f} m3/s ({q / 2831.7:.1f} lakh cusec)"
         + (f", lead time {a.lead}" if a.lead else ""),
         f"(flow = {PRED} at Naraj, the measure the atlas is fitted on; method: {method})",
         f"Expected flooded land: {summary['flooded_land_km2']:,.0f} km2"
         + (" (lower bound: flow above the largest in the 2017-2026 radar record)" if lower_bound else ""),
         f"People living on that land: {summary['people_on_flooded_land']:,}",
         f"Settlements with at least 10 % of people on flooded land: {len(hit)}"]
for _, r in hit.head(15).iterrows():
    lines.append(f"  - {r['name']}: about {int(r.people):,} people ({r.share:.0%} of {int(r['pop']):,}) at {r.lat:.4f} N, {r.lon:.4f} E")
lines.append(f"Main roads under water: {summary['main_road_km_under_water']} km"
             + ("; named sections: " + ", ".join(f"{k} {v} km" for k, v in summary["main_roads_affected"].items())
                if summary["main_roads_affected"] else ""))
lines.append("Source: Sentinel-1 flood atlas 2017-2026 + GloFAS discharge (IIT Bombay IDP prototype). Not an official warning.")
open(f"{a.out}/bulletin_{tag}.txt", "w", encoding="utf-8").write("\n".join(lines) + "\n")

# CAP 1.2 alert, the format the Rakshak Control Centre accepts: one circle per settlement to warn. Status "Exercise",
# because this is a prototype and not an official warning.
now = datetime.now(timezone(timedelta(hours=5, minutes=30))).replace(microsecond=0).isoformat()
people_ = summary["people_on_flooded_land"]
severity = "Extreme" if people_ >= 20000 else "Severe" if people_ >= 5000 else "Moderate"
areas = "".join(f"<area><areaDesc>{escape(str(r['name']))}: about {int(r.people):,} people on flooded land</areaDesc>"
                f"<circle>{r.lat:.4f},{r.lon:.4f} {a.alert_km}</circle></area>" for _, r in hit.head(30).iterrows())
cap = ('<?xml version="1.0" encoding="UTF-8"?>\n<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">'
       f"<identifier>prithvi-flood-in-{tag}-{now[:19].replace(':', '')}</identifier>"
       f"<sender>prithvi-flood-in.iitb.prototype</sender><sent>{now}</sent><status>Exercise</status>"
       "<msgType>Alert</msgType><scope>Public</scope><info><language>en-IN</language><category>Met</category>"
       f"<event>River flood</event><urgency>Expected</urgency><severity>{severity}</severity><certainty>Possible</certainty>"
       f"<headline>Mahanadi delta: flooding expected at a Naraj flow of {q:,.0f} m3/s</headline>"
       f"<description>{escape(chr(10).join(lines))}</description>"
       "<instruction>Follow the district administration; keep off flooded roads.</instruction>"
       f"{areas}</info></alert>\n")
open(f"{a.out}/bulletin_{tag}.cap.xml", "w", encoding="utf-8").write(cap)
print("\n".join(lines))
