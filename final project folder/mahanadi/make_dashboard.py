"""Self-contained HTML viewer of the atlas and the impact analyses (the 'flood-extent layer' prototype).

    ATLAS_DIR=... IMPACT_DIR=... python mahanadi/make_dashboard.py <checkpoints_dir> <out.html>

Rasters are re-projected to Web Mercator (EPSG:3857) at 40 m and embedded as PNG overlays, so they sit exactly
on any web map; vectors are embedded as GeoJSON. Works offline: an own basemap (main roads, river bed) is
embedded, OpenStreetMap tiles are added when the browser is online.
"""
import base64
import io
import json
import os
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from PIL import Image
from rasterio.features import rasterize
from rasterio.warp import Resampling, calculate_default_transform, reproject, transform_bounds

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from impact_common import ATLAS, IMPACT, osm, read, read_all  # noqa: E402

CP, OUT = sys.argv[1], sys.argv[2]
with rasterio.open(f"{ATLAS}/flood_frequency.tif") as src:
    SRC = dict(crs=src.crs, transform=src.transform, width=src.width, height=src.height)
    bounds = src.bounds
dst_t, dw, dh = calculate_default_transform(SRC["crs"], "EPSG:3857", SRC["width"], SRC["height"], *bounds, resolution=40)
w, s, e, n = transform_bounds("EPSG:3857", "EPSG:4326", dst_t.c, dst_t.f + dh * dst_t.e, dst_t.c + dw * dst_t.a, dst_t.f)
LL = [[s, w], [n, e]]


def to3857(arr, resampling=Resampling.max):
    out = np.zeros((dh, dw), np.float32)
    reproject(arr.astype(np.float32), out, src_transform=SRC["transform"], src_crs=SRC["crs"], dst_transform=dst_t,
              dst_crs="EPSG:3857", resampling=resampling, src_nodata=np.nan, dst_nodata=np.nan)
    return out


def png(rgba):
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def mask_png(m, rgb, alpha=190):
    m3 = to3857(m.astype(np.float32)) > 0.5
    rgba = np.zeros((dh, dw, 4), np.uint8)
    rgba[m3] = [*rgb, alpha]
    return png(rgba)


def classes_png(cls, colors):
    c3 = to3857(np.where(np.isnan(cls), np.nan, cls), Resampling.nearest)
    rgba = np.zeros((dh, dw, 4), np.uint8)
    for i, col in enumerate(colors):
        rgba[np.isfinite(c3) & (np.round(c3) == i)] = [*col, 200]
    return png(rgba)


normal = read(f"{ATLAS}/normal_water_latest.tif").astype(bool)
S = json.load(open(f"{ATLAS}/atlas_summary.json"))
RP = {int(k): v for k, v in S["gumbel"]["return_period_m3s"].items()}

# own basemap: river bed + main roads
roads = osm("roads", SRC["crs"])
main = roads[roads.highway.isin(["trunk", "primary", "secondary", "tertiary", "trunk_link", "primary_link"])]
rr = rasterize(((g, 1) for g in main.geometry), out_shape=(SRC["height"], SRC["width"]), transform=SRC["transform"], dtype="uint8")
base = np.zeros((dh, dw, 4), np.uint8)
base[..., :3] = (237, 241, 245)  # the site's map land colour
base[..., 3] = 255
base[to3857(normal.astype(np.float32)) > 0.5] = [190, 205, 222, 255]
base[to3857(rr.astype(np.float32)) > 0.5] = [150, 150, 150, 255]
layers = {"basemap": png(base)}

# frequency classes and trigger discharge classes
freq = read(f"{ATLAS}/flood_frequency.tif").astype(np.float32)
fc = np.full(freq.shape, np.nan, np.float32)
for i, (lo, hi) in enumerate([(1, 5), (5, 10), (10, 20), (20, 30), (30, 50), (50, 101)]):
    fc[(freq >= lo) & (freq < hi) & (freq != 255) & ~normal] = i
blues = [(198, 219, 239), (158, 202, 225), (107, 174, 214), (66, 146, 198), (33, 113, 181), (8, 69, 148)]
layers["frequency"] = classes_png(fc, blues)
theta = read(f"{ATLAS}/trigger_discharge.tif").astype(np.float32)
tc = np.full(theta.shape, np.nan, np.float32)
edges = [-1, RP[2], RP[5], RP[10], RP[25], 9e5]
for i in range(5):
    tc[(theta > edges[i]) & (theta <= edges[i + 1]) & ~normal] = i
oranges = [(127, 39, 4), (196, 70, 7), (241, 105, 19), (253, 141, 60), (253, 190, 133)]
layers["trigger"] = classes_png(tc, oranges)

# scenarios
bands, desc = read_all(f"{ATLAS}/scenarios_return_period.tif")
Ts = [int(t) for t in desc.split("T ")[1].split(" years")[0].split(",")]
scen = {f"T{T}": b.astype(bool) & ~normal for T, b in zip(Ts, bands)}
with rasterio.open(f"{ATLAS}/observed_largest_flood.tif") as src:
    obs, tag = src.read(1), src.tags()["description"]
obs_key = f"observed_{tag.split('S1_')[1][:8]}"
scen[obs_key] = (obs == 1) & ~normal
if os.path.exists(f"{ATLAS}/scenario_heavy_rain.tif"):
    scen["rain_T5"] = read(f"{ATLAS}/scenario_heavy_rain.tif").astype(bool) & ~normal
for k, m in scen.items():
    layers[f"scen_{k}"] = mask_png(m, (240, 135, 20), 200)  # flood orange, as on the project site
if os.path.exists(f"{IMPACT}/ground_zone_T25.tif"):  # geotechnical advisory zone (impact_ground.py)
    layers["ground"] = mask_png(read(f"{IMPACT}/ground_zone_T25.tif").astype(bool), (91, 33, 182), 170)
if os.path.exists(f"{IMPACT}/depth_T25.tif"):  # structural screening: >= 1 m deep (impact_depth.py)
    dd = read(f"{IMPACT}/depth_T25.tif")
    layers["deep"] = mask_png((dd != 255) & (dd >= 10), (127, 29, 29), 220)

ex = pd.read_csv(f"{IMPACT}/exposure_scenarios.csv").set_index("scenario")
tr = pd.read_csv(f"{IMPACT}/transport_scenarios.csv").set_index("scenario") if os.path.exists(f"{IMPACT}/transport_scenarios.csv") else pd.DataFrame()
st = pd.read_csv(f"{IMPACT}/settlements.csv")
acc = pd.read_csv(f"{IMPACT}/settlement_access.csv") if os.path.exists(f"{IMPACT}/settlement_access.csv") else None
info = {}
for k in scen:
    e = ex.loc[k] if k in ex.index else None
    t = tr.loc[k] if k in tr.index else None
    col = f"flooded_share_{k}"
    vil = st.assign(people=st["pop"] * st[col]).sort_values("people", ascending=False) if col in st else st.head(0)
    vil = vil[vil[col] >= 0.10].head(40) if col in st else vil
    cut = set()
    if acc is not None and f"hospital_min_{k}" in acc:
        cut = set(acc.loc[(acc["hospital_min_dry"] >= 0) & (acc[f"hospital_min_{k}"] < 0), "settlement"])
    q = RP.get(int(k[1:])) if k.startswith("T") else (RP.get(5) if k == "rain_T5" else None)
    hr = S.get("heavy_rain_scenario", {})
    info[k] = dict(
        label=(f"{k[1:]}-year flood" if k.startswith("T") else
               (f"5-year flow + heavy local rain ({hr.get('rain_mm', 0)} mm)" if k == "rain_T5"
                else f"largest observed ({tag.split('(')[1].split(',')[0]})")),
        q=round(q) if q else None, lakh=round(q / 2831.7, 1) if q else None,
        stats=None if e is None else {
            "Flooded land (km²)": e["flood_km2"], "People on flooded land": int(e["people"]),
            "Cropland flooded (km²)": e["cropland km2"], "Roads under water (km)": e["road km (all)"],
            "Bridges with flooded approach": int(e["bridges with flooded approach"]),
            "Health facilities in flood": int(e["health facilities"]), "Schools in flood": int(e["schools"]),
            "Settlements ≥10 % flooded": int(e["settlements >= 10 % of people flooded"]),
            **({} if t is None else {"People cut off from hospital": int(t["hospital: people cut off"]),
                                     "Settlements cut off from hospital": int(t["hospital: settlements cut off"])})},
        villages=[dict(name=r["name"], pop=int(r["pop"]), share=round(float(r[col]) * 100), lat=round(r.lat, 5),
                       lon=round(r.lon, 5), cut=bool(r["settlement"] in cut)) for _, r in vil.iterrows()])
    fr = f"{IMPACT}/flooded_roads_{k}.geojson"
    if os.path.exists(fr):
        g = gpd.read_file(fr).to_crs(32645)
        g["geometry"] = g.geometry.simplify(15)
        info[k]["roads"] = json.loads(g.to_crs(4326).to_json(drop_id=True))


def pts(csv, cols):
    p = f"{IMPACT}/{csv}" if not csv.startswith("/") else csv
    if not os.path.exists(p):
        return []
    d = pd.read_csv(p)
    return [{c: (None if pd.isna(r[c]) else (r[c].item() if hasattr(r[c], "item") else r[c])) for c in cols if c in d}
            for _, r in d.iterrows()]


vec = dict(sirens=pts("siren_sites.csv", ["rank", "settlement", "lat", "lon", "new_people_covered", "cumulative_share"]),
           sensors=pts("sensor_sites.csv", ["river", "name", "ref", "length_m", "access_dry", "lat", "lon"]),
           geotech=pts("geotech_top20.csv", ["rank", "lat", "lon", "priority", "behind_freq", "years_flooded", "texture"]),
           links=[r for r in pts("critical_links.csv", ["scenario", "rank", "road", "highway", "people_routed", "flooded_km", "lat", "lon"])],
           checkpoints=pts(f"{CP}/checkpoints.csv", ["id", "kind", "lat", "lon", "note"]))
towns = {"Cuttack": [20.4625, 85.8830], "Naraj (delta head)": [20.475, 85.775], "Kendrapara": [20.5, 86.4167],
         "Jagatsinghpur": [20.2556, 86.1706], "Salepur": [20.484, 86.11]}
data = dict(bounds=LL, layers=layers, info=info, vec=vec, towns=towns, rp={str(k): round(v) for k, v in RP.items()},
            summary=dict(passes=S["n_passes"], monsoon=S["n_monsoon"], years=S["years"], predictor=S["predictor"],
                         validation=S["validation"]["high_flow_passes"], threshold=S.get("threshold")))
html = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_template.html"), encoding="utf-8").read()
import requests  # noqa: E402  (Leaflet's stylesheet is inlined: only scripts may come from a CDN in an artifact page)
css = requests.get("https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css", timeout=60).text
html = html.replace("/*__LEAFLET_CSS__*/", css).replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
open(OUT, "w", encoding="utf-8").write(html)
print("written", OUT, f"{os.path.getsize(OUT) / 1e6:.1f} MB")
