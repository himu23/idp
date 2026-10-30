"""How the flood and its impacts grow with the river flow: the tables a live forecast reads.

    ATLAS_DIR=runs/_atlas/build_r20 IMPACT_DIR=runs/_atlas/impact_r20 python mahanadi/impact_curve.py

The trigger map gives every 20 m pixel the flow above which it is usually flooded, so the flood at any flow q is the
land with trigger <= q (the design-flood maps are exactly this at the Gumbel flows). Sweeping q once answers, for any
later forecast, what floods and who is affected, without running a model:
impact_curve.csv            per flow: flooded land, people on it, cropland, settlements with >= 10 % of their people on
                            flooded land, health facilities and schools with flood water within 60 m, road km cut and,
                            when the roads carry OSM node ids (Overpass), people cut off from every hospital, also with
                            the ten critical links of cm_plan.py raised (never cut)
settlement_thresholds.csv   per settlement: the flow at which >= 10 % and >= 50 % of its people are on flooded land and
                            the flow at which it loses road access to every hospital
road_cut_flows.csv          per OSM way: the lowest flow at which >= 20 m of one of its edges is under water (the rule of
                            impact_transport.py; bridges are never cut)
facility_thresholds.csv     per health facility and school: the flow at which flood water comes within 60 m
Above the largest flow seen by radar the map stops growing (a lower bound); the curve flags those rows.
The sweep reproduces the design-flood numbers of impact_exposure.py and impact_transport.py (checked at the end).
"""
import json
import os

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy import ndimage
from scipy.sparse.csgraph import dijkstra

from impact_common import ATLAS, CTX, IMPACT, PIX_KM2, Grid, dump, line_samples, osm, read, road_graph

g = Grid()
to_ll = Transformer.from_crs(g.crs, 4326, always_xy=True)
AS = json.load(open(f"{ATLAS}/atlas_summary.json"))
RP = {int(k): float(v) for k, v in AS["gumbel"]["return_period_m3s"].items()}
QMAX = float(AS["largest_observed_predictor_m3s"])
theta = read(f"{ATLAS}/trigger_discharge.tif").astype(np.float64)
normal = read(f"{ATLAS}/normal_water_latest.tif").astype(bool)
trig = np.where(np.isfinite(theta) & ~normal & (theta < 1e6), theta, np.inf)  # flow at which each land pixel floods
pop = np.nan_to_num(read(f"{CTX}/grid20_pop.tif").astype(np.float64))
crop = read(f"{CTX}/grid20_worldcover.tif") == 40
levels = np.unique(np.r_[np.arange(500, np.ceil(RP[100] / 1000) * 1000 + 1, 250), list(RP.values()), QMAX].round(1))
print(f"{len(levels)} flow levels up to {levels.max():,.0f} m3/s; largest seen {QMAX:,.0f}", flush=True)

# ------------------------------------------------------------------ land, people, cropland
fin = np.isfinite(trig)
order = np.argsort(trig[fin], kind="stable")
tv = trig[fin][order]
cpop = np.r_[0, np.cumsum(pop[fin][order])]
ccrop = np.r_[0, np.cumsum(crop[fin][order])]
n_at = np.searchsorted(tv, levels, side="right")
curve = pd.DataFrame(dict(q_m3s=levels, flooded_km2=(n_at * PIX_KM2).round(2), people=cpop[n_at].round(),
                          cropland_km2=(ccrop[n_at] * PIX_KM2).round(2), beyond_record=levels > QMAX))

# ------------------------------------------------------------------ settlements
st = pd.read_csv(f"{IMPACT}/settlements.csv")
lab = read(f"{IMPACT}/settlement_labels.tif")
sel = (lab > 0) & fin
px = pd.DataFrame(dict(s=lab[sel], t=trig[sel], p=pop[sel])).sort_values(["s", "t"], kind="stable")
px["share"] = px.groupby("s").p.cumsum() / px.s.map(st.set_index("settlement")["pop"]).clip(lower=1)
for frac, col in ((0.10, "q_flood10"), (0.50, "q_flood50")):
    st[col] = st.settlement.map(px[px.share >= frac].groupby("s").t.first())
curve["settlements_10pct"] = [(st.q_flood10 <= q).sum() for q in levels]

# ------------------------------------------------------------------ health facilities and schools (water within 60 m)
near = ndimage.minimum_filter(np.where(fin, trig, 1e12), size=7)  # 3 pixels each way = 60 m, as in the exposure counts
fac = []
for kind, layer in (("health", "health"), ("school", "schools")):
    f = osm(layer, g.crs)
    if len(f):
        c = f.geometry.centroid
        qf = g.sample(near, c.x.values, c.y.values, 1e12)
        lon, lat = to_ll.transform(c.x.values, c.y.values)
        fac.append(pd.DataFrame(dict(kind=kind, name=f.get("name", pd.Series(index=f.index, dtype=object)).values,
                                     lon=np.round(lon, 5), lat=np.round(lat, 5), q_flood60m=np.where(qf < 1e11, qf, np.nan))))
fac = pd.concat(fac, ignore_index=True) if fac else pd.DataFrame(columns=["kind", "name", "lon", "lat", "q_flood60m"])
for kind in ("health", "school"):
    qs = fac.q_flood60m[fac.kind == kind]
    curve[f"{kind}_facilities_flooded"] = [(qs <= q).sum() for q in levels]

# ------------------------------------------------------------------ roads: flow at which >= 20 m of an edge is wet
roads = osm("roads", g.crs)
routing = "nodes" in roads.columns
if routing:
    R = road_graph(g, roads)
    e_of, sx, sy, seg, n_edges, way, bridge = R.eidx, R.sx, R.sy, R.seglen, len(R.u), R.WAY, R.BR
else:  # roads from the Geofabrik extract: no node ids, so no routing, but the same 20 m rule per line
    e_of, sx, sy, seg = line_samples(roads.geometry.values)
    n_edges, way = len(roads), np.arange(len(roads))
    bridge = roads.get("bridge", pd.Series(index=roads.index, dtype=object)).fillna("no").ne("no").values
ts = g.sample(trig, sx, sy, np.inf)
o = np.lexsort((ts, e_of))
e_s, t_s, l_s = e_of[o], ts[o], seg[o]
starts = np.r_[0, np.flatnonzero(np.diff(e_s)) + 1]
cum = np.cumsum(l_s)
cum_in = cum - np.repeat(cum[starts] - l_s[starts], np.diff(np.r_[starts, len(e_s)]))
hit = (cum_in >= 20) & np.isfinite(t_s)
eh, th = e_s[hit], t_s[hit]
first = np.r_[True, eh[1:] != eh[:-1]] if len(eh) else np.array([], bool)
cutq = np.full(n_edges, np.inf)
cutq[eh[first]] = th[first]
cutq[bridge] = np.inf
elen = np.bincount(e_of, weights=seg, minlength=n_edges)
curve["road_km_cut"] = [round(elen[cutq <= q].sum() / 1000, 2) for q in levels]
rw = pd.DataFrame(dict(way=way, cutq=cutq, len_m=elen)).query("cutq < inf")
wf = rw.groupby("way").cutq.min()
geo = roads.iloc[wf.index].geometry.centroid
lon, lat = to_ll.transform(geo.x.values, geo.y.values)
road_cut = pd.DataFrame(dict(osm_id=roads.iloc[wf.index].get("osm_id").values,
                             name=roads.iloc[wf.index].get("name", pd.Series(index=roads.index, dtype=object)).values,
                             ref=roads.iloc[wf.index].get("ref", pd.Series(index=roads.index, dtype=object)).values,
                             highway=roads.iloc[wf.index].get("highway").values, cut_flow=wf.values.round(),
                             lon=np.round(lon, 5), lat=np.round(lat, 5))).sort_values("cut_flow")

# ------------------------------------------------------------------ hospital access (Overpass roads only)
st["q_cut_hospital"] = np.nan
if routing:
    health = osm("health", g.crs)
    hosp = health[health.get("amenity").isin(["hospital", "clinic"]) |
                  health.get("healthcare", pd.Series(index=health.index, dtype=object)).isin(["hospital", "clinic", "centre"])]
    hn = np.unique(R.snap(hosp.geometry.centroid.x.values, hosp.geometry.centroid.y.values))
    hn = hn[hn >= 0]
    node = R.snap(st.x.values, st.y.values)
    on = node >= 0
    reach0 = on & np.isfinite(dijkstra(R.G0, directed=False, indices=hn, min_only=True)[np.maximum(node, 0)])
    q_cut = np.full(len(st), np.nan)
    # the ten links cm_plan.py raises (critical links of the 25-year flood): never cut in the second sweep
    cl_path = f"{IMPACT}/critical_links.csv"
    top = pd.read_csv(cl_path).query("scenario == 'T25'").head(10).osm_id if os.path.exists(cl_path) else []
    cutq_raised = np.where(np.isin(roads.osm_id.values[way], list(top)), np.inf, cutq)
    cut_people, cut_sett, cut_raised = [], [], []
    for q in levels:
        d = dijkstra(R.matrix(~(cutq <= q)), directed=False, indices=hn, min_only=True)
        lost = reach0 & ~np.isfinite(d[np.maximum(node, 0)])
        q_cut[lost & np.isnan(q_cut)] = q
        cut_people.append(round(st["pop"].values[lost].sum()))
        cut_sett.append(int(lost.sum()))
        d_r = dijkstra(R.matrix(~(cutq_raised <= q)), directed=False, indices=hn, min_only=True)
        cut_raised.append(round(st["pop"].values[reach0 & ~np.isfinite(d_r[np.maximum(node, 0)])].sum()))
    st["q_cut_hospital"] = q_cut
    curve["hospital_people_cut_off"], curve["hospital_settlements_cut_off"] = cut_people, cut_sett
    curve["hospital_people_cut_off_links_raised"] = cut_raised

# ------------------------------------------------------------------ outputs and the check against the scenario runs
curve.to_csv(f"{IMPACT}/impact_curve.csv", index=False)
st[["settlement", "name", "lon", "lat", "pop", "q_flood10", "q_flood50", "q_cut_hospital"]].to_csv(
    f"{IMPACT}/settlement_thresholds.csv", index=False, float_format="%.1f")
road_cut.to_csv(f"{IMPACT}/road_cut_flows.csv", index=False)
fac.to_csv(f"{IMPACT}/facility_thresholds.csv", index=False, float_format="%.1f")
check = {}
exp = json.load(open(f"{IMPACT}/exposure_summary.json"))["scenarios"]
tr_path = f"{IMPACT}/transport_summary.json"  # only where impact_transport.py has run (the Mahanadi)
tr = {r["scenario"]: r for r in json.load(open(tr_path))["scenarios"]} if routing and os.path.exists(tr_path) else {}
for T in (2, 5, 25):
    row = curve[np.isclose(curve.q_m3s, round(RP[T], 1))].iloc[0]
    e = exp.get(f"T{T}", {})
    check[f"T{T}"] = dict(flooded_km2=[float(row.flooded_km2), e.get("flood_km2")], people=[float(row.people), e.get("people")],
                          settlements_10pct=[int(row.settlements_10pct), e.get("settlements >= 10 % of people flooded")])
    if routing and tr:
        check[f"T{T}"]["hospital_people_cut_off"] = [int(row.hospital_people_cut_off),
                                                     tr.get(f"T{T}", {}).get("hospital: people cut off")]
dump(dict(levels=len(levels), q_max_seen_m3s=round(QMAX), routing=routing, settlements=len(st),
          settlements_ever_10pct=int(st.q_flood10.notna().sum()), roads_with_cut_flow=len(road_cut),
          facilities=len(fac), check_against_scenarios=check), f"{IMPACT}/impact_curve_summary.json")
print(json.dumps(check, indent=1))
print("CURVE_DONE", flush=True)
