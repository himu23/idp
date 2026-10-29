"""Where to put warning sirens and river sensors: the planning input for a ClimMaTech-style deployment.

    python mahanadi/impact_siting.py [--k 40] [--design T25]

Sirens: greedy maximal-coverage location. Demand = GHSL people living on land that floods in the design flood
(default: the 25-year flood, or anything flooded in >= 10 % of the monsoon passes), on 100 m cells. Candidates =
settlements of >= 1,000 people (a siren goes on a school or panchayat building). A siren covers demand within R m; the
Rakshak audible range is not published, so R = 1.0, 1.5 and 2.0 km are all reported and 1.5 km is listed.
River sensors: one non-contact radar (level + surface velocity) per main distributary, on the most upstream road
bridge of that river inside the AOI (nearest to the delta apex at Naraj) that crosses >= 100 m of normal water and
whose approaches stay dry in the design flood (so the site can be reached during a flood).
Outputs in runs/_atlas/impact: siren_sites.csv, siren_coverage_curve.csv, sensor_sites.csv, siting_summary.json
"""
import argparse

import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer
from scipy.spatial import cKDTree

from impact_common import CTX, IMPACT, Grid, dump, grow, line_samples, osm, read, scenarios

ap = argparse.ArgumentParser()
ap.add_argument("--k", type=int, default=40)
ap.add_argument("--design", default="T25")
a = ap.parse_args()
g = Grid()
scen, normal = scenarios(g)
to_ll = Transformer.from_crs(g.crs, 4326, always_xy=True)
from_ll = Transformer.from_crs(4326, g.crs, always_xy=True)
hazard = scen[a.design] | scen["freq10"]

# ------------------------------------------------------------------ sirens
popr = np.nan_to_num(read(f"{CTX}/grid20_pop.tif").astype(np.float64)) * hazard
H5, W5 = g.H // 5 * 5, g.W // 5 * 5
p100 = popr[:H5, :W5].reshape(H5 // 5, 5, W5 // 5, 5).sum((1, 3))
rr, cc = np.nonzero(p100 > 0.5)
dx, dy = g.xy(rr * 5 + 2, cc * 5 + 2)
d = pd.DataFrame(dict(x=dx, y=dy, pop=p100[rr, cc]))
st = pd.read_csv(f"{IMPACT}/settlements.csv")
cand = st[st["pop"] >= 1000].reset_index(drop=True)
total = d["pop"].sum()
print(f"design hazard: {hazard.sum() * 400 / 1e6:.0f} km2, {total:,.0f} people in {len(d):,} 100 m cells; "
      f"{len(cand):,} candidate settlements", flush=True)
dtree = cKDTree(d[["x", "y"]].values)
pop = d["pop"].values
curves, chosen = [], {}
for R in (1000, 1500, 2000):
    cover = dtree.query_ball_point(cand[["x", "y"]].values, R)
    cover = [np.array(c, dtype=int) for c in cover]
    covered = np.zeros(len(d), bool)
    gain = np.array([pop[c].sum() for c in cover])
    picks = []
    for k in range(a.k):
        i = int(np.argmax(gain))
        if gain[i] <= 0:
            break
        new = cover[i][~covered[cover[i]]]
        covered[new] = True
        picks.append((i, pop[new].sum()))
        gain = np.array([pop[c[~covered[c]]].sum() for c in cover])  # exact recompute (few thousand candidates)
        curves.append(dict(radius_m=R, sirens=k + 1, people_covered=round(pop[covered].sum()),
                           share=round(pop[covered].sum() / total, 3)))
    chosen[R] = picks
    print(f"R={R} m: {len(picks)} sirens cover {pop[covered].sum() / total:.0%} of the exposed people", flush=True)
rows, cum = [], 0
for rank, (i, newpop) in enumerate(chosen[1500], 1):
    cum += newpop
    c = cand.iloc[i]
    rows.append(dict(rank=rank, settlement=c["name"], lon=round(c.lon, 5), lat=round(c.lat, 5),
                     settlement_pop=round(c["pop"]), new_people_covered=round(newpop), cumulative_share=round(cum / total, 3)))
pd.DataFrame(rows).to_csv(f"{IMPACT}/siren_sites.csv", index=False)
pd.DataFrame(curves).to_csv(f"{IMPACT}/siren_coverage_curve.csv", index=False)

# ------------------------------------------------------------------ river sensors
roads = osm("roads", g.crs)
br = roads[roads["bridge"].notna() & (roads["bridge"] != "no")].reset_index(drop=True)
idx, x, y, ln = line_samples(br.geometry.values, 10.0)
on_water = g.sample(normal.astype(np.uint8), x, y, 0).astype(bool)
water_m = np.bincount(idx, weights=ln * on_water, minlength=len(br))
br["water_m"] = water_m
br["length_m"] = shapely.length(br.geometry.values)
major = br[br.water_m >= 100].copy()
F3 = grow(scen[a.design], 3)
ends = np.array([[geom.coords[0], geom.coords[-1]] for geom in major.geometry])
major["access_dry"] = ~(g.sample(F3, ends[:, 0, 0], ends[:, 0, 1], False) | g.sample(F3, ends[:, 1, 0], ends[:, 1, 1], False))
rivers = osm("waterways", g.crs)
rivers = rivers[(rivers["waterway"] == "river") & rivers["name"].notna()]
mid = major.geometry.interpolate(0.5, normalized=True)
if len(rivers):
    near = rivers.sindex.nearest(mid.values, return_all=False, return_distance=True)
    (src_i, riv_i), dist = near
    major["river"] = None
    major.iloc[src_i, major.columns.get_loc("river")] = np.where(dist < 600, rivers["name"].values[riv_i], None)
apex = np.array(from_ll.transform(85.775, 20.475))  # Naraj, head of the delta
major["km_from_naraj"] = np.hypot(mid.x - apex[0], mid.y - apex[1]) / 1000
lon, lat = to_ll.transform(mid.x.values, mid.y.values)
major["lon"], major["lat"] = np.round(lon, 5), np.round(lat, 5)
major["people_in_hazard_10km"] = [round(pop[dtree.query_ball_point(p, 10000)].sum()) for p in np.c_[mid.x, mid.y]]
sel = []
for riv, grp in major[major.river.notna()].groupby("river"):
    grp = grp.sort_values(["access_dry", "km_from_naraj"], ascending=[False, True])
    sel.append(grp.iloc[0])
sensors = pd.DataFrame(sel)
cols = ["river", "name", "ref", "highway", "length_m", "water_m", "access_dry", "km_from_naraj", "lon", "lat",
        "people_in_hazard_10km"]
R1 = {"length_m": 1, "water_m": 1, "km_from_naraj": 1, "lon": 5, "lat": 5}  # never round coordinates to 0.1 deg (~11 km)
sensors = sensors[[c for c in cols if c in sensors]].sort_values("km_from_naraj").round(R1)
sensors.to_csv(f"{IMPACT}/sensor_sites.csv", index=False)
major[[c for c in cols if c in major]].round(R1).to_csv(f"{IMPACT}/major_bridges.csv", index=False)
print(sensors.to_string(index=False), flush=True)
dump(dict(design=a.design, hazard_km2=round(hazard.sum() * 400 / 1e6, 1), exposed_people=round(total),
          candidates=len(cand), coverage={R: next((c for c in reversed(curves) if c["radius_m"] == R), None) for R in (1000, 1500, 2000)},
          sirens_for_80pct_at_1500m=next((c["sirens"] for c in curves if c["radius_m"] == 1500 and c["share"] >= 0.8), None),
          major_bridges=len(major), sensor_sites=len(sensors)), f"{IMPACT}/siting_summary.json")
print("SITING_DONE")
