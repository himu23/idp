"""Who and what is exposed in each flood scenario: people, mapped buildings, farmland, roads, bridges, railways,
health facilities, schools; and the settlement layer that the transport, siting and geotechnical analyses use.

    python mahanadi/impact_exposure.py

People: GHSL 2020 population (3 arc-second grid resampled to people per 20 m pixel; 4.1 million in the AOI).
Settlements: 20 m pixels above 1,000 people/km2, dilated by one pixel, 8-connected, >= 200 people; centroid
population-weighted. Names: each OSM place name goes to its nearest settlement of >= 1,000 people within 2 km;
the others are labelled "near <place> (km)".
Buildings: Microsoft Global ML Building Footprints. Coverage of this part of India is incomplete (~120 k
footprints for ~4 M people), so building counts are reported as "mapped buildings" only.
Outputs in runs/_atlas/impact: settlements.csv, pop100.parquet, exposure_scenarios.csv, facilities_flooded.csv,
exposure_summary.json
"""
import os

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy import ndimage
from scipy.spatial import cKDTree

from impact_common import CTX, IMPACT, PIX_KM2, WC, Grid, dump, grow, line_samples, osm, read, scenarios

os.makedirs(IMPACT, exist_ok=True)
g = Grid()
scen, normal = scenarios(g)
to_ll = Transformer.from_crs(g.crs, 4326, always_xy=True)
pop = np.nan_to_num(read(f"{CTX}/grid20_pop.tif").astype(np.float64))

# ------------------------------------------------------------------ settlements from the population grid
core = pop / PIX_KM2 >= 1000
lab, n = ndimage.label(ndimage.binary_dilation(core, iterations=1), structure=np.ones((3, 3)))
ids = np.arange(1, n + 1)
spop = ndimage.sum(pop, lab, ids)
keep = ids[spop >= 200]
cent = np.array(ndimage.center_of_mass(pop, lab, keep))
x, y = g.xy(cent[:, 0], cent[:, 1])
st = pd.DataFrame(dict(settlement=keep, pop=np.round(spop[keep - 1]), area_km2=ndimage.sum(np.ones_like(pop), lab, keep) * PIX_KM2,
                       x=x, y=y))
st["lon"], st["lat"] = to_ll.transform(st.x.values, st.y.values)
st["name"] = None
places = osm("places", g.crs)
if len(places):
    pname = (places["name_en"] if "name_en" in places else places["name"]).fillna(places["name"]).values
    big = np.where(st["pop"].values >= 1000)[0]
    tb = cKDTree(st.iloc[big][["x", "y"]].values)
    for (px, py), nm in zip(np.c_[places.geometry.x, places.geometry.y], pname):
        if isinstance(nm, str):
            d, i = tb.query([px, py])
            if d < 2000:
                st.iloc[big[i], st.columns.get_loc("name")] = nm
    named = st[st.name.notna()]
    d, i = cKDTree(named[["x", "y"]].values).query(st[["x", "y"]].values)
    miss = st.name.isna().values
    st.loc[miss, "name"] = [f"near {named.name.values[j]} ({dd / 1000:.1f} km)" for dd, j in zip(d[miss], i[miss])]
print(f"population {pop.sum():,.0f}; settlements >= 200 people: {len(st):,} holding {st['pop'].sum():,.0f}; "
      f"named from OSM: {(~st.name.str.startswith('near')).sum()}", flush=True)
g.save(f"{IMPACT}/settlement_labels.tif", np.where(np.isin(lab, keep), lab, 0), "int32", 0)
# 100 m population points (for coverage / proximity analyses)
B = 5
H5, W5 = g.H // B * B, g.W // B * B
p100 = pop[:H5, :W5].reshape(H5 // B, B, W5 // B, B).sum((1, 3))
rr, cc = np.nonzero(p100 > 0)
px, py = g.xy(rr * B + 2, cc * B + 2)
pd.DataFrame(dict(r100=rr, c100=cc, x=px, y=py, pop=p100[rr, cc])).to_parquet(f"{IMPACT}/pop100.parquet")

# ------------------------------------------------------------------ assets
bld = pd.read_parquet(f"{CTX}/buildings.parquet")
br_, bc_, ok = g.rc(bld.x.values, bld.y.values)
br_, bc_ = br_[ok], bc_[ok]
roads = osm("roads", g.crs)
is_bridge = (roads["bridge"].notna() & (roads["bridge"] != "no")).values if "bridge" in roads else np.zeros(len(roads), bool)
ridx, rx, ry, rl = line_samples(roads.geometry.values, 10.0)
rclass = roads["highway"].values[ridx]
rails = osm("railways", g.crs)
lidx, lx, ly, ll = line_samples(rails.geometry.values, 10.0) if len(rails) else (np.array([], int),) * 4
bridges = roads[is_bridge]
e0 = np.array([geom.coords[0] for geom in bridges.geometry])
e1 = np.array([geom.coords[-1] for geom in bridges.geometry])
health = osm("health", g.crs)
if len(health):
    hc = health["healthcare"] if "healthcare" in health else pd.Series(index=health.index, dtype=object)
    health = health[health["amenity"].isin(["hospital", "clinic"]) | hc.isin(["hospital", "clinic", "centre"])].copy()
schools = osm("schools", g.crs)
wc = read(f"{CTX}/grid20_worldcover.tif")
MAIN = ["trunk", "primary", "secondary", "tertiary"]
MAIN += [m + "_link" for m in MAIN]

rows, fac_rows = [], []
for name, F in scen.items():
    F3 = grow(F, 3)  # within 60 m, for point facilities and bridge ends
    rec = dict(scenario=name, flood_km2=round(F.sum() * PIX_KM2, 1), people=round(pop[F].sum()),
               mapped_buildings=int(F[br_, bc_].sum()))
    for k, lbl in WC.items():
        rec[f"{lbl} km2"] = round(((wc == k) & F).sum() * PIX_KM2, 1)
    fl = g.sample(F, rx, ry, False) & ~is_bridge[ridx]
    rec["road km (all)"] = round(rl[fl].sum() / 1000, 1)
    rec["road km (trunk-tertiary)"] = round(rl[fl & np.isin(rclass, MAIN)].sum() / 1000, 1)
    rec["rail km"] = round(ll[g.sample(F, lx, ly, False)].sum() / 1000, 1) if len(lx) else 0
    cut = g.sample(F3, e0[:, 0], e0[:, 1], False) | g.sample(F3, e1[:, 0], e1[:, 1], False)
    rec["bridges with flooded approach"] = int(cut.sum())
    hp = health.geometry.centroid if len(health) else None
    sp = schools.geometry.centroid if len(schools) else None
    hf = g.sample(F3, hp.x.values, hp.y.values, False) if hp is not None else np.array([], bool)
    sf = g.sample(F3, sp.x.values, sp.y.values, False) if sp is not None else np.array([], bool)
    rec["health facilities"] = int(hf.sum())
    rec["schools"] = int(sf.sum())
    share = ndimage.sum(pop * F, lab, st.settlement.values) / np.maximum(st["pop"].values, 1)
    st[f"flooded_share_{name}"] = np.round(share, 3)
    rec["settlements >= 10 % of people flooded"] = int((share >= 0.10).sum())
    rec["settlements >= 50 % of people flooded"] = int((share >= 0.50).sum())
    rows.append(rec)
    for kind, pts, gdf, flag in (("health", hp, health, hf), ("school", sp, schools, sf)):
        if pts is None:
            continue
        for k in np.where(flag)[0]:
            lon, lat = to_ll.transform(pts.x.values[k], pts.y.values[k])
            f = gdf.iloc[k]
            fac_rows.append(dict(scenario=name, kind=kind, name=f.get("name"), amenity=f.get("amenity"),
                                 lon=round(lon, 5), lat=round(lat, 5)))
    print(rec, flush=True)

ex = pd.DataFrame(rows)
ex.to_csv(f"{IMPACT}/exposure_scenarios.csv", index=False)
pd.DataFrame(fac_rows).to_csv(f"{IMPACT}/facilities_flooded.csv", index=False)
st.to_csv(f"{IMPACT}/settlements.csv", index=False, float_format="%.5f")
dump(dict(population_ghsl=round(pop.sum()), settlements=len(st), settlement_population=round(st["pop"].sum()),
          mapped_buildings_ms=int(ok.sum()), road_km_total=round(rl.sum() / 1000), bridges=int(is_bridge.sum()),
          health_facilities=len(health), schools=len(schools),
          scenarios=ex.set_index("scenario").to_dict("index")), f"{IMPACT}/exposure_summary.json")
print("EXPOSURE_DONE")
