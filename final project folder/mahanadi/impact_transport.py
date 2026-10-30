"""Road-network disruption (transportation engineering): which settlements lose road access to a hospital or a
town in each flood scenario, how much longer the trip becomes, and which flooded road links matter most.

    python mahanadi/impact_transport.py

Graph: OSM motorable roads (nodes = OSM nodes, edges = consecutive node pairs, two-way). Travel time from typical
rural speeds per road class (SPEED in impact_common.py, km/h). An edge is impassable when >= 20 m of it lies in flood water;
bridges are never cut (deck above water) but their approaches can be.
Origins: settlements from impact_exposure.py, snapped to the nearest node of the main network within 500 m.
Destinations: OSM hospitals/clinics, and towns (OSM place = city/town) as service centres.
Critical links: in the dry-weather shortest-path forest to the nearest hospital, each edge carries the population
of the settlements routed through it; flooded edges with the largest load are the links to raise or protect first.
Evacuation: time to the nearest school with no flood water within 60 m (schools serve as relief camps).
Daily delay: extra round-trip time to the nearest town x 0.2 trips per person per day (an assumed trip rate, for
the order of magnitude of the travel cost of a flood).
Outputs in runs/_atlas/impact: transport_scenarios.csv, critical_links.csv, settlement_access.csv,
flooded_roads_<scenario>.geojson
"""
import json

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer
from scipy.sparse.csgraph import dijkstra

from impact_common import IMPACT, SPEED, Grid, dump, grow, osm, road_graph, scenarios

g = Grid()
scen, _ = scenarios(g)
to_ll = Transformer.from_crs(g.crs, 4326, always_xy=True)

# ------------------------------------------------------------------ graph
roads = osm("roads", g.crs)
R = road_graph(g, roads)
ids, nxy, u, v, X0, Y0, X1, Y1 = R.ids, R.nxy, R.u, R.v, R.X0, R.Y0, R.X1, R.Y1
length, minutes, WAY, BR, N = R.length, R.minutes, R.WAY, R.BR, R.N
eidx, sx, sy, seglen, matrix, G0, snap = R.eidx, R.sx, R.sy, R.seglen, R.matrix, R.G0, R.snap
print(f"road graph: {N:,} nodes, {len(u):,} edges, {length.sum() / 1000:,.0f} km", flush=True)

st = pd.read_csv(f"{IMPACT}/settlements.csv")
st["node"] = snap(st.x.values, st.y.values)
health = osm("health", g.crs)
hosp = health[health.get("amenity").isin(["hospital", "clinic"]) |
              health.get("healthcare", pd.Series(index=health.index, dtype=object)).isin(["hospital", "clinic", "centre"])]
places = osm("places", g.crs)
towns = places[places["place"].isin(["city", "town"])]
dest = {"hospital": np.unique(snap(hosp.geometry.centroid.x.values, hosp.geometry.centroid.y.values)),
        "town": np.unique(snap(towns.geometry.x.values, towns.geometry.y.values))}
dest = {kk: d[d >= 0] for kk, d in dest.items()}
print("destinations:", {kk: len(d) for kk, d in dest.items()}, "settlements on the network:",
      int((st.node >= 0).sum()), "of", len(st), flush=True)


def access(Gm, targets):
    dist, pred, _ = dijkstra(Gm, directed=False, indices=targets, min_only=True, return_predecessors=True)
    return dist, pred


on = st.node.values >= 0
base = {kk: access(G0, d) for kk, d in dest.items()}
# Shelters: schools double as relief camps in Odisha floods; a school is usable only if no flood water within 60 m
schools = osm("schools", g.crs)
sc_xy = np.c_[schools.geometry.centroid.x.values, schools.geometry.centroid.y.values] if len(schools) else np.zeros((0, 2))
sc_node = snap(sc_xy[:, 0], sc_xy[:, 1]) if len(sc_xy) else np.array([], int)
TRIPS_PER_PERSON_DAY = 0.2  # trips to the nearest town per person per day (assumption, for an order of magnitude)
for kk in dest:
    st[f"{kk}_min_dry"] = np.where(on, base[kk][0][np.maximum(st.node.values, 0)], np.inf)

# population load per edge on the dry-weather routes to the nearest hospital
dist0, pred0 = base["hospital"]
acc = np.zeros(N)
np.add.at(acc, st.node.values[on], st["pop"].values[on])
edge_of = {}
for e, (a_, b_) in enumerate(zip(u, v)):
    key = (min(a_, b_), max(a_, b_))
    if key not in edge_of or minutes[e] < minutes[edge_of[key]]:
        edge_of[key] = e
load = np.zeros(len(u))
for n in np.argsort(-np.where(np.isfinite(dist0), dist0, -1)):
    p = pred0[n]
    if p >= 0 and np.isfinite(dist0[n]):
        e = edge_of.get((min(n, p), max(n, p)))
        if e is not None:
            load[e] += acc[n]
        acc[p] += acc[n]

rows, crit = [], []
for name, F in scen.items():
    wet = np.zeros(len(u))
    np.add.at(wet, eidx, seglen * g.sample(F, sx, sy, False))
    cut = (wet >= 20) & ~BR
    Gf = matrix(~cut)
    rec = dict(scenario=name, edges_cut=int(cut.sum()), road_km_cut=round(length[cut].sum() / 1000, 1))
    # evacuation: time to the nearest school that stays dry
    if len(sc_node):
        dry_sc = ~g.sample(grow(F, 3), sc_xy[:, 0], sc_xy[:, 1], False) & (sc_node >= 0)
        ds = access(Gf, np.unique(sc_node[dry_sc]))[0] if dry_sc.any() else np.full(N, np.inf)
        ts = np.where(on, ds[np.maximum(st.node.values, 0)], np.inf)
        rec["shelter: dry schools"] = int(dry_sc.sum())
        rec["shelter: people > 30 min from a dry school"] = round(st["pop"].values[on & (ts > 30)].sum())
        rec["shelter: people with no reachable dry school"] = round(st["pop"].values[on & ~np.isfinite(ts)].sum())
    for kk, d in dest.items():
        dist_f, _ = access(Gf, d)
        t0 = st[f"{kk}_min_dry"].values
        t1 = np.where(on, dist_f[np.maximum(st.node.values, 0)], np.inf)
        st[f"{kk}_min_{name}"] = np.round(t1, 1)
        lost = np.isfinite(t0) & ~np.isfinite(t1)
        slower = np.isfinite(t1) & (t1 > t0 + 5)
        rec[f"{kk}: settlements cut off"] = int(lost.sum())
        rec[f"{kk}: people cut off"] = round(st["pop"].values[lost].sum())
        rec[f"{kk}: people with trip +5 min or more"] = round(st["pop"].values[slower].sum())
        rec[f"{kk}: median extra minutes (still reachable, delayed)"] = round(float(np.median((t1 - t0)[slower])), 1) if slower.any() else 0
        if kk == "town":
            extra = np.where(np.isfinite(t1) & np.isfinite(t0), np.maximum(t1 - t0, 0), 0)
            rec["town: extra person-hours of travel per day"] = round(float(
                (st["pop"].values * TRIPS_PER_PERSON_DAY * 2 * extra / 60).sum()))
    rows.append(rec)
    # critical links: flooded ways ranked by the population whose dry-weather hospital route uses them
    ce = np.where(cut & (load > 0))[0]
    if len(ce):
        df = pd.DataFrame(dict(way=WAY[ce], load=load[ce], x=(X0[ce] + X1[ce]) / 2, y=(Y0[ce] + Y1[ce]) / 2,
                               km=length[ce] / 1000))
        agg = df.groupby("way").agg(people_routed=("load", "max"), flooded_km=("km", "sum"), x=("x", "mean"), y=("y", "mean"))
        agg = agg.sort_values("people_routed", ascending=False).head(15)
        lon, lat = to_ll.transform(agg.x.values, agg.y.values)
        for (w, r_), lo, la in zip(agg.iterrows(), lon, lat):
            rw = roads.iloc[w]
            crit.append(dict(scenario=name, rank=len([c for c in crit if c["scenario"] == name]) + 1,
                             road=rw.get("name") if isinstance(rw.get("name"), str) else rw.get("ref"),
                             highway=rw["highway"], osm_id=rw["osm_id"], people_routed=round(r_.people_routed),
                             flooded_km=round(r_.flooded_km, 2), lon=round(lo, 5), lat=round(la, 5)))
    geoms = [shapely.LineString([(X0[e], Y0[e]), (X1[e], Y1[e])]) for e in np.where(cut)[0]]
    if geoms:
        gpd.GeoDataFrame(dict(minutes=minutes[cut]), geometry=geoms, crs=g.crs).dissolve().to_crs(4326).to_file(
            f"{IMPACT}/flooded_roads_{name}.geojson", driver="GeoJSON")
    print(rec, flush=True)

pd.DataFrame(rows).to_csv(f"{IMPACT}/transport_scenarios.csv", index=False)
pd.DataFrame(crit).to_csv(f"{IMPACT}/critical_links.csv", index=False)
cols = ["settlement", "name", "lon", "lat", "pop"] + [c for c in st.columns if c.endswith(tuple(
    ["_dry"] + [f"_{s}" for s in scen]))]
st[cols].replace(np.inf, -1).to_csv(f"{IMPACT}/settlement_access.csv", index=False, float_format="%.1f")
dump(dict(nodes=N, edges=len(u), road_km=round(length.sum() / 1000), speeds_kmh=SPEED,
          destinations={kk: len(d) for kk, d in dest.items()}, scenarios=rows), f"{IMPACT}/transport_summary.json")
print("TRANSPORT_DONE")
