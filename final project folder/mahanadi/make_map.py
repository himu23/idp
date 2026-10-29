"""Interactive map (folium) and static figure of the Mahanadi flood products.

    python mahanadi/make_map.py <model_name>

Reads runs/_mahanadi/<event>_<model>_classes.tif, writes runs/_mahanadi/mahanadi_map.html
(OpenStreetMap basemap so roads and villages are visible under the flood layer) and a
static PNG panel per event.
"""
import json
import sys

import folium
import matplotlib
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.warp import Resampling, calculate_default_transform, reproject

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = "/home1/vineet/floodfm/runs/_mahanadi"
DATA = "/home1/vineet/floodfm/data/mahanadi"
model = sys.argv[1]
summary = json.load(open(f"{OUT}/summary.json"))
PLACES = [("Cuttack", 20.4625, 85.8830, "city"), ("Kendrapara", 20.5017, 86.4220, "town"),
          ("Naraj barrage (CWC gauge, Mahanadi)", 20.4700, 85.7790, "gauge"),
          ("Jagatsinghpur", 20.2549, 86.1706, "town"),
          ("Hirakud Dam (upstream, ~230 km)", 21.5267, 83.8722, "dam")]
COLORS = {1: (42, 120, 214), 2: (227, 73, 72)}   # permanent/normal water blue, flood water red

m = folium.Map(location=[20.45, 86.12], zoom_start=10, tiles="OpenStreetMap", control_scale=True)
for ev, info in summary["events"].items():
    path = f"{OUT}/{ev}_{model}_classes.tif"
    try:
        src = rasterio.open(path)
    except Exception:
        continue
    tr, w, h = calculate_default_transform(src.crs, "EPSG:4326", src.width, src.height, *src.bounds)
    dst = np.full((h, w), 255, np.uint8)
    reproject(rasterio.band(src, 1), dst, src_transform=src.transform, src_crs=src.crs, dst_transform=tr,
              dst_crs="EPSG:4326", resampling=Resampling.nearest)
    rgba = np.zeros((h, w, 4), np.uint8)
    for k, c in COLORS.items():
        rgba[dst == k] = (*c, 190)
    west, north = tr * (0, 0)
    east, south = tr * (w, h)
    date = ev.split("_")[1]
    a = info["models"][model]
    folium.raster_layers.ImageOverlay(
        rgba, bounds=[[south, west], [north, east]], name=f"{date[:4]}-{date[4:6]}-{date[6:]}: flood {a['flood_km2']:.0f} km²",
        show=(ev == "event_20220816")).add_to(m)
for name, lat, lon, kind in PLACES:
    icon = {"dam": "tint", "gauge": "signal", "city": "home", "town": "home"}[kind]
    folium.Marker([lat, lon], tooltip=name, icon=folium.Icon(color="darkblue" if kind in ("dam", "gauge") else "gray",
                                                               icon=icon)).add_to(m)
folium.LayerControl(collapsed=False).add_to(m)
legend = ("<div style='position:fixed;bottom:24px;left:24px;z-index:9999;background:white;padding:8px 10px;"
          "border-radius:6px;font:12px sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.3)'>"
          "<b>Sentinel-1 flood map (model: " + model + ")</b><br>"
          "<span style='color:#e34948'>&#9632;</span> flood water (new vs dry season)<br>"
          "<span style='color:#2a78d6'>&#9632;</span> normal / permanent water<br>"
          "Demonstration only: no ground truth for these dates</div>")
m.get_root().html.add_child(folium.Element(legend))
m.save(f"{OUT}/mahanadi_map.html")

# static figure: radar VH on event date, dry-season VH, classes
events = [e for e in summary["events"] if e != "dry"]
fig, axes = plt.subplots(len(events), 3, figsize=(12, 3.4 * len(events)))
axes = np.atleast_2d(axes)
for r, ev in enumerate(events):
    info = summary["events"][ev]
    with rasterio.open(f"{DATA}/{ev}/s1_vv_vh_db.tif") as s:
        vh = s.read(2)[::4, ::4]
    with rasterio.open(f"{DATA}/{info['dry_reference']}/s1_vv_vh_db.tif") as s:
        vhd = s.read(2)[::4, ::4]
    with rasterio.open(f"{OUT}/{ev}_{model}_classes.tif") as s:
        cl = s.read(1)[::4, ::4]
    rgb = np.full(cl.shape + (3,), 0.94)
    rgb[cl == 1] = np.array(COLORS[1]) / 255
    rgb[cl == 2] = np.array(COLORS[2]) / 255
    rgb[cl == 255] = 1.0
    a = info["models"][model]
    for c, (img, t) in enumerate([(np.clip(vh, -28, -8), f"Sentinel-1 VH, {ev.split('_')[1]}"),
                                  (np.clip(vhd, -28, -8), f"VH dry season, {info['dry_reference'].split('_')[1]}"),
                                  (rgb, f"flood {a['flood_km2']:.0f} km² (red), normal water blue")]):
        axes[r, c].imshow(img, cmap="gray" if c < 2 else None)
        axes[r, c].set_title(t, fontsize=9)
        axes[r, c].axis("off")
fig.suptitle("Mahanadi delta (85.80–86.45°E, 20.25–20.65°N), radar-only model " + model, fontsize=10)
fig.tight_layout()
fig.savefig(f"{OUT}/mahanadi_panels.png", dpi=110)
print("map + panels written")
