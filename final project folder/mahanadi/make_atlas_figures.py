"""Figures for the report, the slides and the printed field dossier, from the atlas and impact outputs.

    ATLAS_DIR=... IMPACT_DIR=... python mahanadi/make_atlas_figures.py <out_dir> [<checkpoints_dir>]

Maps are drawn in UTM 45N kilometres with towns labelled for orientation; colours: one hue light -> dark for
magnitudes (frequency, trigger discharge), grey for normal water, roads faint. dossier.pdf = the maps plus the
check-point table, for printing before the visit.
"""
import json
import os
import sys

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import rasterio
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.collections import LineCollection
from matplotlib.colors import BoundaryNorm, ListedColormap
from pyproj import Transformer

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from impact_common import ATLAS, CTX, IMPACT, osm, read, read_all  # noqa: E402

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
                     "savefig.dpi": 160, "savefig.bbox": "tight"})
INK, MUTED, WATER, ROAD = "#1f2328", "#6e7781", "#9fb3c8", "#c9ced6"
TOWNS = {"Cuttack": (85.8830, 20.4625), "Naraj": (85.775, 20.475), "Kendrapara": (86.4167, 20.5000),
         "Jagatsinghpur": (86.1706, 20.2556), "Salepur": (86.1100, 20.4840), "Tangi": (85.995, 20.395)}
with rasterio.open(f"{ATLAS}/flood_frequency.tif") as src:
    T, CRS, H, W = src.transform, src.crs, src.height, src.width
EXT = [T.c / 1000, (T.c + W * T.a) / 1000, (T.f + H * T.e) / 1000, T.f / 1000]
to_xy = Transformer.from_crs(4326, CRS, always_xy=True)
normal = read(f"{ATLAS}/normal_water_latest.tif").astype(bool)
roads = osm("roads", CRS)
roads = roads[roads.highway.isin(["trunk", "primary", "secondary", "tertiary", "trunk_link", "primary_link"])]
S = json.load(open(f"{ATLAS}/atlas_summary.json"))
RP = {int(k): v for k, v in S["gumbel"]["return_period_m3s"].items()}


ROAD_SEGS = [np.asarray(part.coords)[:, :2] / 1000 for geom in roads.geometry for part in getattr(geom, "geoms", [geom])]


def base(ax, title):
    ax.imshow(np.where(normal, 1, np.nan), extent=EXT, cmap=ListedColormap([WATER]), interpolation="nearest", zorder=1)
    ax.add_collection(LineCollection(ROAD_SEGS, colors=ROAD, linewidths=0.4, zorder=2))
    for name, (lon, lat) in TOWNS.items():
        x, y = to_xy.transform(lon, lat)
        ax.plot(x / 1000, y / 1000, "s", ms=3, color=INK, zorder=6)
        ax.annotate(name, (x / 1000, y / 1000), xytext=(3, 3), textcoords="offset points", fontsize=8, color=INK, zorder=6)
    ax.set_xlim(EXT[0], EXT[1])
    ax.set_ylim(EXT[2], EXT[3])
    ax.set_xlabel("Easting (km, UTM 45N)", color=MUTED)
    ax.set_ylabel("Northing (km)", color=MUTED)
    ax.tick_params(colors=MUTED, labelsize=7)
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    ax.plot([EXT[1] - 12, EXT[1] - 2], [EXT[2] + 2, EXT[2] + 2], color=INK, lw=2)
    ax.text(EXT[1] - 7, EXT[2] + 2.6, "10 km", ha="center", fontsize=7)


figs = {}

# 1. time series: discharge (top) and flooded area (bottom), shared time axis
passes = pd.read_csv(f"{ATLAS}/atlas_passes.csv", parse_dates=["date"])
Q = pd.read_csv(f"{CTX}/discharge.csv", index_col="date", parse_dates=True)["naraj"]
Q = Q[Q.index >= "2017-01-01"]
fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 5), sharex=True, gridspec_kw=dict(height_ratios=[1, 1.2]))
a1.plot(Q.index, Q.values / 1000, color="#3b6ea8", lw=0.8)
for T_, q in RP.items():
    if T_ in (2, 10, 25):
        a1.axhline(q / 1000, color=MUTED, lw=0.6, ls=":")
        a1.text(Q.index[-1], q / 1000, f" {T_}-yr", va="center", fontsize=7, color=MUTED)
a1.set_ylabel("Naraj discharge\n(1000 m³/s, GloFAS)")
for orb, col in (("descending", "#1f77b4"), ("ascending", "#d95f02")):
    d = passes[passes.orbit_state == orb]
    a2.scatter(d.date, d.flood_km2, s=14, color=col, alpha=0.8, label=f"{orb} pass", edgecolor="white", lw=0.4)
a2.set_ylabel("Flooded land on the pass (km²)")
a2.legend(frameon=False, fontsize=8, loc="upper left")
a1.set_title("River flow at the delta head and flooded land seen by each Sentinel-1 pass (Jun–Nov)", loc="left", fontsize=10)
fig.savefig(f"{OUT}/atlas_timeseries.png")
plt.close(fig)

# 2. flooded fraction vs discharge
fig, ax = plt.subplots(figsize=(5.5, 4))
sc = ax.scatter(passes.q / 1000, passes.flood_frac * 100, c=passes.date.dt.month, cmap="viridis", s=16, edgecolor="white", lw=0.3)
cb = fig.colorbar(sc, ax=ax, ticks=[6, 7, 8, 9, 10, 11])
cb.ax.set_yticklabels(["Jun", "Jul", "Aug", "Sep", "Oct", "Nov"])
bins = np.arange(0, passes.q.max() / 1000 + 4, 4)
med = passes.groupby(pd.cut(passes.q / 1000, bins)).flood_frac.median() * 100
ax.plot([iv.mid for iv in med.index], med.values, color=INK, lw=2, label="median per 4,000 m³/s bin")
ax.set_xlabel(f"Naraj discharge, {S['predictor'].replace('_', ' ')} (1000 m³/s)")
ax.set_ylabel("Flooded share of observed land (%)")
ax.legend(frameon=False, fontsize=8)
ax.set_title(f"Flood extent rises with river flow (Spearman ρ = {S['predictor_spearman'][S['predictor']]:.2f})", loc="left", fontsize=10)
fig.savefig(f"{OUT}/atlas_area_vs_discharge.png")
plt.close(fig)

# 3. flood frequency map
freq = read(f"{ATLAS}/flood_frequency.tif").astype(float)
freq[(freq == 255) | normal] = np.nan
freq[freq == 0] = np.nan
fig, ax = plt.subplots(figsize=(10, 6.8))
base(ax, f"Flood frequency 2017–2026: share of monsoon radar passes on which the land was flooded")
bounds = [1, 5, 10, 20, 30, 50, 100]
cmap = ListedColormap(plt.cm.Blues(np.linspace(0.35, 1.0, len(bounds) - 1)))
im = ax.imshow(freq, extent=EXT, cmap=cmap, norm=BoundaryNorm(bounds, cmap.N), interpolation="nearest", zorder=3)
cb = fig.colorbar(im, ax=ax, shrink=0.7)
cb.set_label("% of monsoon passes flooded")
fig.savefig(f"{OUT}/atlas_frequency_map.png")
figs["frequency"] = f"{OUT}/atlas_frequency_map.png"
plt.close(fig)

# 4. trigger discharge map in design-flood classes
theta = read(f"{ATLAS}/trigger_discharge.tif").astype(float)
cls = np.full(theta.shape, np.nan)
edges = [0, RP[2], RP[5], RP[10], RP[25], 1e5]
labels = [f"< {RP[2] / 1000:.0f}k (2-yr)", f"{RP[2] / 1000:.0f}–{RP[5] / 1000:.0f}k (2–5 yr)",
          f"{RP[5] / 1000:.0f}–{RP[10] / 1000:.0f}k (5–10 yr)", f"{RP[10] / 1000:.0f}–{RP[25] / 1000:.0f}k (10–25 yr)",
          f"> {RP[25] / 1000:.0f}k (rarer)"]
for i in range(5):
    cls[(theta > edges[i] if i else theta >= 0) & (theta <= edges[i + 1]) & (theta < 1e6) & ~normal] = i
cls[(theta == 0) & ~normal] = 0
fig, ax = plt.subplots(figsize=(10, 6.8))
base(ax, "Trigger discharge: the Naraj flow (m³/s) at which each pixel starts to flood")
cmap = ListedColormap(plt.cm.Oranges(np.linspace(1.0, 0.3, 5)))
im = ax.imshow(cls, extent=EXT, cmap=cmap, vmin=-0.5, vmax=4.5, interpolation="nearest", zorder=3)
cb = fig.colorbar(im, ax=ax, shrink=0.7, ticks=range(5))
cb.ax.set_yticklabels(labels, fontsize=7)
cb.set_label("floods when Naraj flow exceeds")
fig.savefig(f"{OUT}/atlas_trigger_map.png")
figs["trigger"] = f"{OUT}/atlas_trigger_map.png"
plt.close(fig)

# 5. river-driven score
auc = read(f"{ATLAS}/river_driven_auc.tif").astype(float)
auc[(auc == 255) | normal | np.isnan(freq)] = np.nan
fig, ax = plt.subplots(figsize=(10, 6.8))
base(ax, "Is the flooding driven by the river? AUC of Naraj discharge between flooded and dry observations")
im = ax.imshow(auc / 100, extent=EXT, cmap="PuBu", vmin=0.5, vmax=1.0, interpolation="nearest", zorder=3)
cb = fig.colorbar(im, ax=ax, shrink=0.7)
cb.set_label("0.5 = unrelated to river flow (rain, paddy) · 1 = only at high river flow")
fig.savefig(f"{OUT}/atlas_river_driven.png")
plt.close(fig)

# 6. leave-one-year-out validation per year (high-flow and all passes)
v = S["validation"]
yrs = sorted(v["per_year"], key=int)
fig, ax = plt.subplots(figsize=(7, 3.2))
x = np.arange(len(yrs))
ax.bar(x - 0.18, [v["per_year"][y]["model"]["iou"] for y in yrs], 0.34, color="#3b6ea8", label="discharge model (trigger map)")
ax.bar(x + 0.18, [v["per_year"][y]["climatology"]["iou"] for y in yrs], 0.34, color="#c9ced6", label="climatology (frequency ≥ 50 %)")
ax.set_xticks(x, yrs)
ax.set_ylabel("IoU of flooded land")
ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper left")
ax.set_ylim(0, 1)
hf = v["high_flow_passes"]
ax.set_title(f"Each year predicted from the other years. High-flow passes (≥ {hf['q90_threshold_m3s']:,} m³/s, n = {hf['n']}): "
             f"model {hf['model']['iou']:.2f} vs climatology {hf['climatology']['iou']:.2f}", loc="left", fontsize=9)
fig.savefig(f"{OUT}/atlas_loyo.png")
plt.close(fig)

# 7-9. impact maps
scen_bands, desc = read_all(f"{ATLAS}/scenarios_return_period.tif")
Ts = [int(t) for t in desc.split("T ")[1].split(" years")[0].split(",")]
T25 = scen_bands[Ts.index(25)].astype(bool) & ~normal


def points(ax, csv, color, marker, label, size=30, text=None):
    p = f"{IMPACT}/{csv}"
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p)
    if d.empty:
        return d
    x, y = to_xy.transform(d.lon.values, d.lat.values)
    ax.scatter(x / 1000, y / 1000, s=size, c=color, marker=marker, edgecolor="white", lw=0.6, zorder=7, label=label)
    if text:
        for xi, yi, t in zip(x, y, d[text]):
            ax.annotate(str(t), (xi / 1000, yi / 1000), xytext=(3, -8), textcoords="offset points", fontsize=6, zorder=8)
    return d


fig, ax = plt.subplots(figsize=(10, 6.8))
base(ax, "25-year flood: flooded land, roads cut, critical links and flooded health facilities")
ax.imshow(np.where(T25, 1, np.nan), extent=EXT, cmap=ListedColormap(["#4f8fd6"]), alpha=0.75, interpolation="nearest", zorder=3)
fr = f"{IMPACT}/flooded_roads_T25.geojson"
if os.path.exists(fr):
    segs = [np.asarray(part.coords)[:, :2] / 1000 for geom in gpd.read_file(fr).to_crs(CRS).geometry
            for part in getattr(geom, "geoms", [geom])]
    ax.add_collection(LineCollection(segs, colors="#b42318", linewidths=1.0, zorder=5))
ax.plot([], [], color="#b42318", lw=1.5, label="road cut (≥ 20 m under water)")
cl = pd.read_csv(f"{IMPACT}/critical_links.csv") if os.path.exists(f"{IMPACT}/critical_links.csv") else pd.DataFrame()
if len(cl):
    c25 = cl[cl.scenario == "T25"].head(10)
    x, y = to_xy.transform(c25.lon.values, c25.lat.values)
    ax.scatter(x / 1000, y / 1000, s=60, facecolor="none", edgecolor=INK, lw=1.2, zorder=7, label="critical link (top 10)")
fac = pd.read_csv(f"{IMPACT}/facilities_flooded.csv") if os.path.exists(f"{IMPACT}/facilities_flooded.csv") else pd.DataFrame()
if len(fac):
    h = fac[(fac.scenario == "T25") & (fac.kind == "health")]
    x, y = to_xy.transform(h.lon.values, h.lat.values)
    ax.scatter(x / 1000, y / 1000, s=28, marker="P", c="#7a2e8e", edgecolor="white", lw=0.5, zorder=7, label="health facility in flood")
ax.legend(frameon=True, fontsize=7, loc="lower left")
fig.savefig(f"{OUT}/impact_T25_map.png")
figs["impact"] = f"{OUT}/impact_T25_map.png"
plt.close(fig)

hazard = T25 | ((read(f"{ATLAS}/flood_frequency.tif") >= 10) & (read(f"{ATLAS}/flood_frequency.tif") != 255) & ~normal)
fig, ax = plt.subplots(figsize=(10, 6.8))
base(ax, "Deployment plan: siren sites (1.5 km coverage) and river-sensor bridges")
ax.imshow(np.where(hazard, 1, np.nan), extent=EXT, cmap=ListedColormap(["#f2b8a2"]), alpha=0.8, interpolation="nearest", zorder=3)
sr = points(ax, "siren_sites.csv", "#b42318", "o", "siren site", 22)
if sr is not None and len(sr):
    x, y = to_xy.transform(sr.lon.values, sr.lat.values)
    for xi, yi in zip(x, y):
        ax.add_patch(plt.Circle((xi / 1000, yi / 1000), 1.5, fill=False, color="#b42318", lw=0.5, alpha=0.6, zorder=6))
points(ax, "sensor_sites.csv", "#1f2328", "^", "river sensor (bridge)", 60, text="river")
ax.legend(frameon=True, fontsize=7, loc="lower left")
fig.savefig(f"{OUT}/siting_map.png")
figs["siting"] = f"{OUT}/siting_map.png"
plt.close(fig)

fig, ax = plt.subplots(figsize=(10, 6.8))
base(ax, "River-bank inspection priority (1 km cells; field list = top 20 at least 3 km apart)")
gc = pd.read_csv(f"{IMPACT}/geotech_cells.csv") if os.path.exists(f"{IMPACT}/geotech_cells.csv") else pd.DataFrame()
if len(gc):
    sc = ax.scatter(gc.x / 1000, gc.y / 1000, c=gc.priority, cmap="Reds", s=14, marker="s", zorder=5, vmin=0.3, vmax=0.9)
    fig.colorbar(sc, ax=ax, shrink=0.7).set_label("priority (mean percentile rank)")
    top = pd.read_csv(f"{IMPACT}/geotech_top20.csv")
    for k, (xi, yi) in enumerate(zip(top.x, top.y), 1):
        ax.annotate(str(k), (xi / 1000, yi / 1000), fontsize=7, ha="center", va="center", color="white", weight="bold", zorder=7,
                    bbox=dict(boxstyle="circle,pad=0.15", fc="#7f1d1d", ec="none"))
fig.savefig(f"{OUT}/geotech_map.png")
figs["geotech"] = f"{OUT}/geotech_map.png"
plt.close(fig)

# dossier: the maps + the check-point list (if generated)
cp = os.path.join(sys.argv[2], "checkpoints.csv") if len(sys.argv) > 2 else ""
with PdfPages(f"{OUT}/dossier.pdf") as pdf:
    for key in ("frequency", "trigger", "impact", "siting", "geotech"):
        img = plt.imread(figs[key])
        fig = plt.figure(figsize=(11.69, 8.27))
        plt.imshow(img)
        plt.axis("off")
        pdf.savefig(fig)
        plt.close(fig)
    if os.path.exists(cp):
        d = pd.read_csv(cp)
        for start in range(0, len(d), 32):
            fig = plt.figure(figsize=(11.69, 8.27))
            plt.axis("off")
            part = d.iloc[start:start + 32]
            tb = plt.table(cellText=part[["id", "kind", "lat", "lon", "note"]].values,
                           colLabels=["id", "kind", "lat", "lon", "note"], loc="upper left", cellLoc="left",
                           colWidths=[0.05, 0.14, 0.07, 0.07, 0.67])
            tb.auto_set_font_size(False)
            tb.set_fontsize(7)
            plt.title("Mahanadi delta field check points (GPX/KML in fieldkit/checkpoints)", loc="left")
            pdf.savefig(fig)
            plt.close(fig)
print("FIGURES_DONE", sorted(os.listdir(OUT)))
