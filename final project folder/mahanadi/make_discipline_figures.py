"""Figures for the structural, geotechnical-ground and ocean analyses.

    ATLAS_DIR=... IMPACT_DIR=... python mahanadi/make_discipline_figures.py <out_dir>
"""
import os
import sys

import matplotlib
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from pyproj import Transformer

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_atlas_figures as base_fig  # noqa: E402  (re-uses its base map; it also redraws its own figures)
from impact_common import IMPACT, read  # noqa: E402

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
base, EXT, CRS = base_fig.base, base_fig.EXT, base_fig.CRS
to_xy = Transformer.from_crs(4326, CRS, always_xy=True)

# depth + wall-risk settlements
if os.path.exists(f"{IMPACT}/depth_T25.tif"):
    dd = read(f"{IMPACT}/depth_T25.tif").astype(float)
    depth = np.where(dd == 255, np.nan, dd / 10)
    fig, ax = plt.subplots(figsize=(10, 6.8))
    base(ax, "25-year flood: estimated water depth (edge-elevation method) and settlements where walls are at risk")
    bounds = [0.01, 0.5, 1.0, 2.0, 6.0]
    cmap = ListedColormap(["#c6dbef", "#6baed6", "#2171b5", "#08306b"])
    im = ax.imshow(np.where(depth > 0.01, depth, np.nan), extent=EXT, cmap=cmap, norm=BoundaryNorm(bounds, cmap.N),
                   interpolation="nearest", zorder=3)
    fig.colorbar(im, ax=ax, shrink=0.7).set_label("depth (m); ≥ 1 m cracks unreinforced 230 mm brick walls")
    if os.path.exists(f"{IMPACT}/wall_risk_settlements.csv"):
        w = pd.read_csv(f"{IMPACT}/wall_risk_settlements.csv").head(30)
        x, y = to_xy.transform(w.lon.values, w.lat.values)
        ax.scatter(x / 1000, y / 1000, s=np.clip(w.people / 20, 10, 120), facecolor="none", edgecolor="#b42318", lw=1.2,
                   zorder=7, label="settlement with ≥ 5 % of people on land deeper than 1 m (size = people)")
        ax.legend(frameon=True, fontsize=7, loc="lower left")
    fig.savefig(f"{OUT}/depth_T25_map.png")
    plt.close(fig)

# ground-saturation advisory
if os.path.exists(f"{IMPACT}/ground_advisory_settlements.csv"):
    from scipy import ndimage
    bands, desc = base_fig.read_all(f"{base_fig.ATLAS}/scenarios_return_period.tif")
    Ts = [int(t) for t in desc.split("T ")[1].split(" years")[0].split(",")]
    F = bands[Ts.index(25)].astype(bool) & ~base_fig.normal
    zone = ndimage.binary_dilation(F, iterations=10) & ~F & ~base_fig.normal
    fig, ax = plt.subplots(figsize=(10, 6.8))
    base(ax, "Ground-saturation advisory, 25-year flood: dry land within 200 m of flood water on silty-clay soil")
    ax.imshow(np.where(F, 1, np.nan), extent=EXT, cmap=ListedColormap(["#4f8fd6"]), alpha=0.6, interpolation="nearest", zorder=3)
    ax.imshow(np.where(zone, 1, np.nan), extent=EXT, cmap=ListedColormap(["#f59e0b"]), alpha=0.8, interpolation="nearest", zorder=4)
    a = pd.read_csv(f"{IMPACT}/ground_advisory_settlements.csv").head(40)
    x, y = to_xy.transform(a.lon.values, a.lat.values)
    ax.scatter(x / 1000, y / 1000, s=18, c="#7f1d1d", zorder=7, label="settlement: ≥ 25 % of people in the advisory zone")
    ax.plot([], [], color="#f59e0b", lw=6, label="advisory zone (foundations soak, settle on drawdown)")
    ax.plot([], [], color="#4f8fd6", lw=6, label="flooded land")
    ax.legend(frameon=True, fontsize=7, loc="lower left")
    fig.savefig(f"{OUT}/ground_advisory_map.png")
    plt.close(fig)

# flood drivers
if os.path.exists(f"{IMPACT}/flood_drivers.csv"):
    dr = pd.read_csv(f"{IMPACT}/flood_drivers.csv").sort_values("date")
    col = {"river": "#3b6ea8", "rain": "#2a9d8f", "cyclone/depression": "#7a2e8e"}

    def colour(t):
        for k in ("cyclone/depression", "rain", "river"):
            if k in t:
                return col[k]
        return "#c9ced6"
    fig, ax = plt.subplots(figsize=(10, 3.6))
    xs = np.arange(len(dr))
    ax.bar(xs, dr.flood_km2, color=[colour(t) for t in dr.drivers])
    ax.set_xticks(xs, [d[2:] for d in dr.date], rotation=60, fontsize=7)
    for i, (t, s_) in enumerate(zip(dr.drivers, dr.system.fillna(""))):
        if s_:
            s_ = ", ".join(sorted({"depression" if x.strip().lower() in ("unnamed", "not_named") else x.strip().split(":")[0]
                                  for x in s_.split(",")}))
            ax.text(i, dr.flood_km2.iloc[i] + 4, s_, rotation=90, fontsize=6, ha="center", va="bottom", color="#333")
    ax.set_ylim(0, dr.flood_km2.max() * 1.45)
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=c, label=k) for k, c in col.items()] + [Patch(facecolor="#c9ced6", label="none above the 90th percentile")]
    ax.legend(handles=handles, frameon=False, fontsize=7, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.3))
    ax.set_ylabel("flooded land on the pass (km²)")
    ax.set_title("The 20 largest floods seen by radar and what drove them (first listed driver colours the bar)", loc="left", fontsize=9)
    fig.savefig(f"{OUT}/flood_drivers.png")
    plt.close(fig)

# bridge scour
if os.path.exists(f"{IMPACT}/bridge_scour.csv"):
    sc = pd.read_csv(f"{IMPACT}/bridge_scour.csv")
    sc = sc[sc["T"] == 100]
    # twin carriageways share a name, so the waterway length keeps each label unique
    sc["label"] = (sc.river.fillna("river not named in OSM") + " — " + sc.bridge.fillna("unnamed").astype(str).str.slice(0, 28)
                   + " (" + sc.linear_waterway_m.round().astype(int).map("{:,} m".format) + ")")
    labs = sc.label.unique()
    fig, ax = plt.subplots(figsize=(9, 0.45 * len(labs) + 1.2))
    for j, (share, c) in enumerate(((0.25, "#9ecae1"), (0.5, "#3b6ea8"), (0.75, "#08306b"))):
        v = sc[sc.share == share].set_index("label").reindex(labs).pier_scour_below_HFL_m
        ax.barh(np.arange(len(labs)) + (j - 1) * 0.27, v.values, 0.25, color=c, label=f"{int(share * 100)} % of the 100-yr flow")
    ax.set_yticks(np.arange(len(labs)), labs, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("maximum scour at piers below HFL (m), IRC:78 Lacey, bed d_m 0.3 mm")
    ax.legend(frameon=False, fontsize=7)
    ax.set_title("Bridge scour screening: depth the pier foundations must go below", loc="left", fontsize=9)
    fig.savefig(f"{OUT}/bridge_scour.png")
    plt.close(fig)
print("DISCIPLINE_FIGURES_DONE", sorted(f for f in os.listdir(OUT) if f.endswith(".png")))
