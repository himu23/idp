"""Helpers shared by the impact_*.py analyses (all on the 20 m atlas grid, UTM 45N)."""
import json
import os
from types import SimpleNamespace

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import shapely
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

HOME = "/home1/vineet/floodfm"
CTX = os.environ.get("CONTEXT_DIR", f"{HOME}/data/mahanadi_context")
ATLAS = os.environ.get("ATLAS_DIR", f"{HOME}/runs/_atlas/build")
IMPACT = os.environ.get("IMPACT_DIR", f"{HOME}/runs/_atlas/impact")
PIX_KM2 = 400 / 1e6
# ESA WorldCover 2021 classes
WC = {10: "tree cover", 20: "shrubland", 30: "grassland", 40: "cropland", 50: "built-up", 60: "bare/sparse",
      80: "permanent water", 90: "herbaceous wetland", 95: "mangroves"}


class Grid:
    def __init__(self, path=f"{ATLAS}/flood_frequency.tif"):
        with rasterio.open(path) as src:
            self.profile, self.t, self.crs = src.profile, src.transform, src.crs
            self.H, self.W = src.height, src.width

    def rc(self, x, y):
        c = np.floor((np.asarray(x) - self.t.c) / self.t.a).astype(np.int64)
        r = np.floor((self.t.f - np.asarray(y)) / -self.t.e).astype(np.int64)
        return r, c, (r >= 0) & (r < self.H) & (c >= 0) & (c < self.W)

    def sample(self, arr, x, y, fill=0):
        r, c, ok = self.rc(x, y)
        out = np.full(r.shape, fill, dtype=arr.dtype)
        out[ok] = arr[r[ok], c[ok]]
        return out

    def xy(self, r, c):
        return self.t.c + (np.asarray(c) + 0.5) * self.t.a, self.t.f + (np.asarray(r) + 0.5) * self.t.e

    def save(self, path, arr, dtype, nodata=None):
        p = dict(self.profile, dtype=dtype, nodata=nodata, count=1, compress="deflate")
        with rasterio.open(path, "w", **p) as dst:
            dst.write(arr.astype(dtype)[None])


def read(path, band=1):
    with rasterio.open(path) as src:
        return src.read(band)


def read_all(path):
    with rasterio.open(path) as src:
        return src.read(), src.tags().get("description", "")


def osm(layer, crs):
    p = f"{CTX}/osm_{layer}.geojson"
    if not os.path.exists(p):
        return gpd.GeoDataFrame(geometry=[], crs=crs)
    return gpd.read_file(p).to_crs(crs)


def line_samples(geoms, step=10.0):
    """Points every ~step m along each line: (line index, x, y, length represented by the point)."""
    geoms = np.asarray(geoms)
    L = shapely.length(geoms)
    n = np.maximum(np.ceil(L / step).astype(int), 1)
    idx = np.repeat(np.arange(len(geoms)), n)
    k = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n)
    d = (k + 0.5) * (L / n)[idx]
    pts = shapely.line_interpolate_point(geoms[idx], d)
    return idx, shapely.get_x(pts), shapely.get_y(pts), (L / n)[idx]


def grow(mask, pixels=1):
    return ndimage.binary_dilation(mask, iterations=pixels) if pixels else mask


def scenarios(grid):
    """Named boolean flood maps (excluding normal water) used by every impact analysis."""
    normal = read(f"{ATLAS}/normal_water_latest.tif").astype(bool)
    out = {}
    bands, desc = read_all(f"{ATLAS}/scenarios_return_period.tif")
    for T, b in zip(desc.split("T ")[1].split(" years")[0].split(","), bands):
        out[f"T{T}"] = b.astype(bool) & ~normal
    freq = read(f"{ATLAS}/flood_frequency.tif")
    out["freq10"] = (freq != 255) & (freq >= 10) & ~normal
    # the largest flood actually observed on a near-complete pass (coverage >= 85 % of the AOI)
    with rasterio.open(f"{ATLAS}/observed_largest_flood.tif") as src:
        obs, tag = src.read(1), src.tags()["description"]
    out[f"observed_{tag.split('S1_')[1][:8]}"] = (obs == 1) & ~normal
    if os.path.exists(f"{ATLAS}/scenario_heavy_rain.tif"):
        out["rain_T5"] = read(f"{ATLAS}/scenario_heavy_rain.tif").astype(bool) & ~normal
    return out, normal


def dump(obj, path):
    json.dump(obj, open(path, "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


# typical rural speeds per OSM road class (km/h)
SPEED = {"trunk": 50, "primary": 40, "secondary": 35, "tertiary": 30, "unclassified": 25, "road": 20,
         "residential": 20, "living_street": 15, "service": 15, "track": 12}


def road_graph(g, roads):
    """OSM motorable roads as a two-way graph (nodes = OSM nodes, edges = consecutive node pairs) with travel minutes
    from SPEED, sample points every ~10 m along each edge for flood look-ups (eidx, sx, sy, seglen), matrix(keep) for
    the graph without the edges where keep is False, and snap() of points to the main component (within 500 m)."""
    U, V, X0, Y0, X1, Y1, SP, WAY, BR = [], [], [], [], [], [], [], [], []
    node_xy = {}
    for w, row in enumerate(roads.itertuples()):
        ids = json.loads(row.nodes) if isinstance(row.nodes, str) else ([] if row.nodes is None else [int(k) for k in row.nodes])
        pts = list(row.geometry.coords)
        if len(ids) != len(pts) or len(ids) < 2:
            continue
        cls = str(row.highway).replace("_link", "")
        br = isinstance(getattr(row, "bridge", None), str) and row.bridge != "no"
        for i in range(len(ids) - 1):
            U.append(ids[i]), V.append(ids[i + 1])
            X0.append(pts[i][0]), Y0.append(pts[i][1]), X1.append(pts[i + 1][0]), Y1.append(pts[i + 1][1])
            SP.append(SPEED.get(cls, 15)), WAY.append(w), BR.append(br)
        for k, p in zip(ids, pts):
            node_xy.setdefault(k, p)
    ids = np.array(list(node_xy))
    pos = {k: i for i, k in enumerate(ids)}
    nxy = np.array([node_xy[k] for k in ids])
    u = np.array([pos[k] for k in U])
    v = np.array([pos[k] for k in V])
    X0, Y0, X1, Y1 = map(np.array, (X0, Y0, X1, Y1))
    length = np.hypot(X1 - X0, Y1 - Y0)
    minutes = length / 1000 / np.array(SP) * 60
    WAY, BR = np.array(WAY), np.array(BR)
    N = len(ids)

    # sample points every ~10 m along each edge (flooded length per scenario)
    nseg = np.maximum(np.ceil(length / 10).astype(int), 1)
    eidx = np.repeat(np.arange(len(u)), nseg)
    k = np.arange(nseg.sum()) - np.repeat(np.cumsum(nseg) - nseg, nseg)
    f = (k + 0.5) / nseg[eidx]
    sx, sy = X0[eidx] + f * (X1 - X0)[eidx], Y0[eidx] + f * (Y1 - Y0)[eidx]
    seglen = (length / nseg)[eidx]

    def matrix(keep):
        m = coo_matrix((np.maximum(minutes[keep], 1e-4), (u[keep], v[keep])), shape=(N, N)).tocsr()
        return m.maximum(m.T)

    G0 = matrix(np.ones(len(u), bool))
    _, comp = connected_components(G0, directed=False)
    main = comp == np.bincount(comp).argmax()
    main_idx = np.where(main)[0]
    tree = cKDTree(nxy[main_idx])

    def snap(x, y, maxd=500):
        d, i = tree.query(np.c_[x, y])
        return np.where(d <= maxd, main_idx[np.minimum(i, len(main_idx) - 1)], -1)

    return SimpleNamespace(ids=ids, nxy=nxy, u=u, v=v, X0=X0, Y0=Y0, X1=X1, Y1=Y1, length=length, minutes=minutes,
                           WAY=WAY, BR=BR, N=N, eidx=eidx, sx=sx, sy=sy, seglen=seglen, matrix=matrix, G0=G0,
                           main_idx=main_idx, snap=snap)
