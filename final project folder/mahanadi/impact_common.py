"""Helpers shared by the impact_*.py analyses (all on the 20 m atlas grid, UTM 45N)."""
import json
import os

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import shapely
from scipy import ndimage

HOME = "/home1/vineet/floodfm"
CTX = f"{HOME}/data/mahanadi_context"
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
