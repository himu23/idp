"""Field-visit check points from the atlas and impact results, as GPX (phone GPS apps), KML (Google Earth /
Maps) and CSV (print).

    python mahanadi/make_checkpoints.py <atlas_dir> <impact_dir> <out_dir>

Ground-truth points: 40, stratified by atlas flood frequency (never / <10 % / 10-30 % / >=30 % of monsoon passes,
10 each), each within 150 m of a road and 1 km of a settlement of >= 1,000 people (somebody to ask), at least
2 km apart, random with a fixed seed. Plus the engineering targets: siren sites, sensor bridges, geotechnical
inspection cells, critical flooded road links and flooded health facilities.
"""
import json
import os
import sys
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from scipy import ndimage
from scipy.spatial import cKDTree

atlas, impact, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
rng = np.random.default_rng(2026)
with rasterio.open(f"{atlas}/flood_frequency.tif") as src:
    freq, t, crs = src.read(1), src.transform, src.crs
to_ll = Transformer.from_crs(crs, 4326, always_xy=True)
to_xy = Transformer.from_crs(4326, crs, always_xy=True)
roads_r = None
try:
    import geopandas as gpd
    from rasterio.features import rasterize
    rd = gpd.read_file("/home1/vineet/floodfm/data/mahanadi_context/osm_roads.geojson").to_crs(crs)
    rd = rd[rd.highway.isin(["trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "track",
                             "trunk_link", "primary_link", "secondary_link", "tertiary_link", "road"])]
    roads_r = rasterize(((geom, 1) for geom in rd.geometry), out_shape=freq.shape, transform=t, dtype="uint8")
except Exception as ex:  # roads are only used to keep points reachable
    print("no road layer:", ex)
near_road = ndimage.distance_transform_edt(roads_r == 0) * 20 <= 150 if roads_r is not None else np.ones(freq.shape, bool)
st = pd.read_csv(f"{impact}/settlements.csv")
st = st[st["pop"] >= 1000]
stree = cKDTree(st[["x", "y"]].values)
strata = {"never flooded": (0, 0), "rarely (<10 %)": (1, 9), "sometimes (10-30 %)": (10, 29), "often (>=30 %)": (30, 100)}
rows = []
for label, (lo, hi) in strata.items():
    rr, cc = np.where((freq >= lo) & (freq <= hi) & near_road)
    order = rng.permutation(len(rr))
    chosen = []
    for k in order:
        x = t.c + (cc[k] + 0.5) * t.a
        y = t.f + (rr[k] + 0.5) * t.e
        if stree.query([x, y])[0] > 1000:
            continue
        if any(np.hypot(x - a, y - b) < 2000 for a, b in chosen) or any(
                np.hypot(x - q["x"], y - q["y"]) < 2000 for q in rows):
            continue
        chosen.append((x, y))
        if len(chosen) == 10:
            break
    for x, y in chosen:
        lon, lat = to_ll.transform(x, y)
        near = st.iloc[stree.query([x, y])[1]]
        rows.append(dict(id=f"GT{len(rows) + 1:02d}", kind="ground truth", lat=round(lat, 6), lon=round(lon, 6),
                         x=x, y=y, note=f"atlas: {label}; ask in {near['name']}"))
pts = pd.DataFrame(rows).drop(columns=["x", "y"])


def add(df, kind, prefix, note):
    if df is None or df.empty:
        return []
    return [dict(id=f"{prefix}{i + 1:02d}", kind=kind, lat=round(r.lat, 6), lon=round(r.lon, 6), note=note(r))
            for i, (_, r) in enumerate(df.iterrows())]


def opt(name, n=None):
    p = f"{impact}/{name}"
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p)
    return df.head(n) if n else df


extra = []
extra += add(opt("siren_sites.csv", 15), "siren site", "SR", lambda r: f"rank {r['rank']}: {r['settlement']}, "
                                                                     f"covers {r['new_people_covered']:,.0f} more people")
extra += add(opt("sensor_sites.csv"), "river sensor bridge", "RS", lambda r: f"{r['river']} bridge, "
                                                                            f"{r['length_m']:.0f} m, approaches dry in the 25-year flood: {'yes' if r['access_dry'] else 'no'}")
extra += add(opt("geotech_top20.csv", 12), "bank inspection / soil sample", "GB",
             lambda r: f"rank {r['rank']}: behind-bank flood freq {r['behind_freq']:.0%}, {r['texture']}")
cl = opt("critical_links.csv")
if cl is not None and len(cl):
    scen = "T25" if (cl.scenario == "T25").any() else cl.scenario.iloc[0]
    extra += add(cl[cl.scenario == scen].head(10), "critical road link", "RL",
                 lambda r: f"{r['road'] if isinstance(r['road'], str) else r['highway']}: {r['people_routed']:,.0f} people's "
                           f"hospital route, {r['flooded_km']} km flooded ({scen})")
extra += add(opt("ground_advisory_settlements.csv", 8), "well levels (ground advisory)", "WL",
             lambda r: f"{r['name']}: {r['share']:.0%} of people within 200 m of 25-yr flood water; measure wells at 0-500 m")
fac = opt("facilities_flooded.csv")
if fac is not None and len(fac):
    f25 = fac[(fac.scenario == "T25") & (fac.kind == "health")].drop_duplicates(["lat", "lon"]).head(10)
    extra += add(f25, "flooded health facility", "HF", lambda r: f"{r['name'] if isinstance(r['name'], str) else r['amenity']}")
allp = pd.concat([pts, pd.DataFrame(extra)], ignore_index=True)
allp.to_csv(f"{out}/checkpoints.csv", index=False)

gpx = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<gpx version="1.1" creator="Prithvi Flood-IN (IIT Bombay IDP)" xmlns="http://www.topografix.com/GPX/1/1">']
for _, p in allp.iterrows():
    gpx.append(f'<wpt lat="{p.lat}" lon="{p.lon}"><name>{escape(p.id)}</name><desc>{escape(p.kind + ": " + str(p.note))}</desc></wpt>')
gpx.append("</gpx>")
open(f"{out}/checkpoints.gpx", "w", encoding="utf-8").write("\n".join(gpx))
kml = ['<?xml version="1.0" encoding="UTF-8"?>', '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
       "<name>Mahanadi delta field visit check points</name>"]
for kind, grp in allp.groupby("kind", sort=False):
    kml.append(f"<Folder><name>{escape(kind)}</name>")
    for _, p in grp.iterrows():
        kml.append(f"<Placemark><name>{escape(p.id)}</name><description>{escape(str(p.note))}</description>"
                   f"<Point><coordinates>{p.lon},{p.lat},0</coordinates></Point></Placemark>")
    kml.append("</Folder>")
kml.append("</Document></kml>")
open(f"{out}/checkpoints.kml", "w", encoding="utf-8").write("\n".join(kml))
print(allp.kind.value_counts().to_string())
json.dump(dict(points=len(allp), by_kind=allp.kind.value_counts().to_dict()), open(f"{out}/checkpoints_summary.json", "w"))
