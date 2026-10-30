"""Fetch the non-satellite context layers for an atlas area (all open data, no login).

    python mahanadi/fetch_context.py --out <dir> [--basin mahanadi] [--only discharge,rain,osm,buildings,rasters,jrc]

discharge.csv        GloFAS v4 daily river discharge (Open-Meteo flood API) at the basin's gauges (Mahanadi: Naraj,
                     Tikarpara and below Hirakud)
rain.csv             ERA5 daily rainfall, mean of 6 points over the box (Open-Meteo archive)
osm_*.geojson        roads, bridges, railways, waterways, embankments, places, health, schools, emergency (Overpass)
buildings.parquet    Microsoft Global ML Building Footprints in the AOI (centroid x/y in UTM, footprint area)
grid20_*.tif         on the 20 m atlas grid (2 x 2 aggregation of the 10 m S1 grid):
                     worldcover (ESA WorldCover 2021 class), dem (Copernicus GLO-30, m), pop (GHSL 2020, people per
                     20 m pixel), sand/silt/clay (SoilGrids 2.0, % in the top 30 cm, depth-weighted)
jrc_occurrence.tif   JRC Global Surface Water occurrence 0-100 % on the 10 m radar grid (where water normally is)
Areas and gauges: basins.py.
"""
import argparse
import gzip
import io
import json
import math
import os
import sys
import time
import zipfile

import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atlas_pull import make_grid  # noqa: E402
from basins import BASINS  # noqa: E402

BBOX = BASINS["mahanadi"]["bbox"]
UA = {"User-Agent": "IITB-IDP-floodstudy/1.0 (academic project)"}
# GloFAS grid cells (Open-Meteo snaps to the nearest 0.05 deg cell); checked by their mean flow in the log
GAUGES = BASINS["mahanadi"]["gauges"]


def grid20():
    g = make_grid(BBOX, 10.0)
    t = g["transform"]
    return dict(crs=g["crs"], transform=rasterio.Affine(20.0, 0, t.c, 0, -20.0, t.f),
                width=g["width"] // 2, height=g["height"] // 2)


def save(path, arr, grid, dtype, nodata=None, desc=None):
    with rasterio.open(path, "w", driver="GTiff", count=1, dtype=dtype, nodata=nodata, compress="deflate",
                       **grid) as dst:
        dst.write(arr.astype(dtype), 1)
        if desc:
            dst.set_band_description(1, desc)


def warp(href, grid, resampling, dtype="float32"):
    with rasterio.open(href) as src, WarpedVRT(src, resampling=resampling, **grid) as v:
        return v.read(1, out_dtype=dtype, masked=True).filled(np.nan if dtype.startswith("float") else 0)


def fetch_discharge(out):
    frames = []
    for name, (lat, lon) in GAUGES.items():
        r = requests.get("https://flood-api.open-meteo.com/v1/flood", headers=UA, timeout=120, params=dict(
            latitude=lat, longitude=lon, daily="river_discharge", start_date="1984-01-01", end_date="2026-10-27"))
        r.raise_for_status()
        d = r.json()
        s = pd.Series(d["daily"]["river_discharge"], index=pd.to_datetime(d["daily"]["time"]), name=name, dtype=float)
        print(f"{name}: GloFAS cell {d['latitude']:.3f},{d['longitude']:.3f} mean {s.mean():.0f} m3/s, "
              f"max {s.max():.0f} on {s.idxmax().date()}", flush=True)
        frames.append(s)
    pd.concat(frames, axis=1).rename_axis("date").to_csv(f"{out}/discharge.csv", float_format="%.1f")


RAIN_PTS = BASINS["mahanadi"]["rain_pts"]


def fetch_rain(out):
    """ERA5 daily precipitation (Open-Meteo archive, IST days), mean of six points over the box."""
    r = requests.get("https://archive-api.open-meteo.com/v1/archive", headers=UA, timeout=300, params=dict(
        latitude=",".join(str(p[0]) for p in RAIN_PTS), longitude=",".join(str(p[1]) for p in RAIN_PTS),
        start_date="2016-01-01", end_date="2026-10-27", daily="precipitation_sum", timezone="Asia/Kolkata"))
    r.raise_for_status()
    series = [pd.Series(d["daily"]["precipitation_sum"], index=pd.to_datetime(d["daily"]["time"]), dtype=float)
              for d in r.json()]
    rain = pd.concat(series, axis=1).mean(axis=1).rename("rain_mm")
    rain.rename_axis("date").to_csv(f"{out}/rain.csv", float_format="%.1f")
    print("rain: mean annual", round(rain.groupby(rain.index.year).sum().mean()), "mm; wettest day",
          rain.idxmax().date(), round(rain.max()), "mm", flush=True)


OVERPASS = {
    "roads": 'way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|'
             'service|track|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|road)$"]',
    "railways": 'way["railway"="rail"]',
    "waterways": 'way["waterway"~"^(river|canal|stream|drain)$"]',
    "embankments": 'way["embankment"="yes"];way["man_made"~"embankment|dyke"]',
    "places": 'node["place"~"^(city|town|village|hamlet|suburb|neighbourhood|locality)$"]',
    "health": 'nwr["amenity"~"^(hospital|clinic|doctors)$"];nwr["healthcare"]',
    "schools": 'nwr["amenity"~"^(school|college|university)$"]',
    "emergency": 'nwr["emergency"];nwr["amenity"="shelter"];nwr["building"="shelter"]',
}


def overpass(query):
    s, w, n, e = BBOX[1], BBOX[0], BBOX[3], BBOX[2]
    parts = "".join(f"{q.strip()}({s},{w},{n},{e});" for q in query.split(";") if q.strip())
    q = f"[out:json][timeout:300];({parts});out body geom;"
    mirrors = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
               "https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass.private.coffee/api/interpreter")
    for attempt in range(4):
        for url in mirrors:
            try:
                r = requests.post(url, data={"data": q}, headers=UA, timeout=400)
                r.raise_for_status()
                return r.json()["elements"]
            except Exception as ex:  # public servers are often busy: try the next mirror, then wait and retry
                print("overpass failed on", url, repr(ex)[:120], flush=True)
        time.sleep(60 * (attempt + 1))
    raise RuntimeError("overpass unavailable")


def fetch_osm(out):
    import geopandas as gpd
    from shapely.geometry import LineString, Point, Polygon
    for layer, q in OVERPASS.items():
        if os.path.exists(f"{out}/osm_{layer}.geojson"):
            continue
        rows = []
        for el in overpass(q):
            tags = el.get("tags", {})
            if el["type"] == "node":
                geom = Point(el["lon"], el["lat"])
            elif el["type"] == "way" and "geometry" in el:
                pts = [(p["lon"], p["lat"]) for p in el["geometry"]]
                if len(pts) < 2:
                    continue
                closed = pts[0] == pts[-1] and len(pts) >= 4
                geom = Polygon(pts).centroid if closed and layer in ("health", "schools", "emergency") else LineString(pts)
            elif el["type"] == "relation" and "center" in el:
                geom = Point(el["center"]["lon"], el["center"]["lat"])
            else:
                continue
            row = {"osm_id": f"{el['type'][0]}{el['id']}", "geometry": geom}
            for k in ("name", "name:en", "highway", "bridge", "railway", "waterway", "place", "amenity", "healthcare",
                      "embankment", "man_made", "layer", "surface", "lanes", "ref", "emergency", "building"):
                if k in tags:
                    row[k.replace(":", "_")] = tags[k]
            if el["type"] == "way" and layer == "roads":
                row["nodes"] = json.dumps(el.get("nodes", []))
            rows.append(row)
        gdf = gpd.GeoDataFrame(rows, crs=4326)
        gdf.to_file(f"{out}/osm_{layer}.geojson", driver="GeoJSON")
        print(f"osm {layer}: {len(gdf)} features", flush=True)


def quadkey(tx, ty, z):
    return "".join(str((1 if tx & (1 << i) else 0) + (2 if ty & (1 << i) else 0)) for i in range(z - 1, -1, -1))


def tile_xy(lat, lon, z):
    s = math.sin(math.radians(lat))
    x = (lon + 180) / 360
    y = 0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)
    return int(x * 2 ** z), int(y * 2 ** z)


def fetch_buildings(out):
    import geopandas as gpd
    from shapely.geometry import shape
    links = pd.read_csv("https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv")
    z = 9
    x0, y0 = tile_xy(BBOX[3], BBOX[0], z)
    x1, y1 = tile_xy(BBOX[1], BBOX[2], z)
    want = {quadkey(x, y, z) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}
    sel = links[(links.Location == "India") & links.QuadKey.astype(str).str.zfill(z).isin(want)]
    print("building tiles:", len(sel), "of", len(want), "quadkeys", flush=True)
    parts = []
    for url in sel.Url:
        r = requests.get(url, headers=UA, timeout=600)
        r.raise_for_status()
        df = pd.read_json(io.BytesIO(gzip.decompress(r.content)), lines=True)
        geoms = [shape(g) for g in df["geometry"]]
        gdf = gpd.GeoDataFrame(geometry=geoms, crs=4326).cx[BBOX[0]:BBOX[2], BBOX[1]:BBOX[3]]
        parts.append(gdf)
        print("  ", url.rsplit("/", 1)[-1], len(gdf), flush=True)
    b = pd.concat(parts, ignore_index=True)
    utm = b.to_crs(make_grid(BBOX)["crs"])
    c = utm.geometry.centroid
    pd.DataFrame({"x": c.x.round(1), "y": c.y.round(1), "area_m2": utm.geometry.area.round(1)}).to_parquet(
        f"{out}/buildings.parquet")
    print("buildings:", len(b), flush=True)


def fetch_rasters(out):
    import planetary_computer as pc
    import pystac_client
    g = grid20()
    cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=pc.sign_inplace)

    wc = np.zeros((g["height"], g["width"]), np.uint8)
    for it in cat.search(collections=["esa-worldcover"], bbox=BBOX, datetime="2021").items():
        a = warp(it.assets["map"].href, g, Resampling.mode, "uint8")
        wc = np.where(wc == 0, a, wc)
    save(f"{out}/grid20_worldcover.tif", wc, g, "uint8", 0, "ESA WorldCover 2021 class")

    dem = np.full((g["height"], g["width"]), np.nan, np.float32)
    for it in cat.search(collections=["cop-dem-glo-30"], bbox=BBOX).items():
        a = warp(it.assets["data"].href, g, Resampling.bilinear)
        dem = np.where(np.isnan(dem), a, dem)
    save(f"{out}/grid20_dem.tif", dem, g, "float32", np.nan, "Copernicus GLO-30 elevation (m, EGM2008)")

    # GHSL population 2020, 3 arc-second tiles (people per cell) -> density -> people per 20 m pixel
    # 10 x 10 degree tiles: row 1 starts at 90 N, column 1 at 180 W (the Mahanadi box is in R7_C27)
    row = int((90 - (BBOX[1] + BBOX[3]) / 2) // 10) + 1
    col = int(((BBOX[0] + BBOX[2]) / 2 + 180) // 10) + 1
    url = ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/"
           f"GHS_POP_E2020_GLOBE_R2023A_4326_3ss/V1-0/tiles/GHS_POP_E2020_GLOBE_R2023A_4326_3ss_V1_0_R{row}_C{col}.zip")
    zf = zipfile.ZipFile(io.BytesIO(requests.get(url, headers=UA, timeout=900).content))
    tif = next(n for n in zf.namelist() if n.endswith(".tif"))
    zf.extract(tif, out)
    with rasterio.open(f"{out}/{tif}") as src:
        lat = (BBOX[1] + BBOX[3]) / 2
        cell_m2 = (src.res[0] * 111320 * math.cos(math.radians(lat))) * (src.res[1] * 110574)
        print("GHSL tile bounds", src.bounds, "cell m2", round(cell_m2), flush=True)
    pop = warp(f"{out}/{tif}", g, Resampling.bilinear)
    pop = np.nan_to_num(np.clip(pop, 0, None)) / cell_m2 * 400.0
    os.remove(f"{out}/{tif}")
    save(f"{out}/grid20_pop.tif", pop, g, "float32", None, "GHSL 2020 population per 20 m pixel")
    print("population in AOI (GHSL):", round(float(pop.sum())), flush=True)

    weights = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}
    for prop in ("sand", "silt", "clay"):
        acc = 0
        try:  # only the geotechnical screening of the Mahanadi uses soils; a failed read does not stop the other layers
            for depth, wgt in weights.items():
                href = f"/vsicurl/https://files.isric.org/soilgrids/latest/data/{prop}/{prop}_{depth}_mean.vrt"
                acc = acc + warp(href, g, Resampling.bilinear) * wgt
        except rasterio.errors.RasterioIOError as ex:
            print("SoilGrids", prop, "not read:", ex, flush=True)
            continue
        pct = acc / sum(weights.values()) / 10.0  # g/kg -> %
        save(f"{out}/grid20_{prop}.tif", pct, g, "float32", np.nan, f"SoilGrids 2.0 {prop} % (0-30 cm)")
        print(prop, "mean %", round(float(np.nanmean(pct)), 1), flush=True)


def fetch_jrc(out):
    """JRC Global Surface Water occurrence (Planetary Computer) on the 10 m radar grid, as pull_s1s2.py makes it."""
    import planetary_computer as pc
    import pystac_client
    g = make_grid(BBOX, 10.0)
    cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=pc.sign_inplace)
    occ = np.zeros((g["height"], g["width"]), np.float32)
    for it in cat.search(collections=["jrc-gsw"], bbox=BBOX).items():
        o = warp(it.assets["occurrence"].href, g, Resampling.nearest)
        occ = np.maximum(occ, np.where(o > 100, 0, o))
    save(f"{out}/jrc_occurrence.tif", occ, g, "uint8", None, "occurrence_pct")
    print("JRC: share of the box with occurrence >= 50 %:", round(float((occ >= 50).mean()), 4), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--basin", default="mahanadi", help="key of basins.py")
    ap.add_argument("--only", default="discharge,buildings,rasters,osm")
    a = ap.parse_args()
    BBOX, GAUGES, RAIN_PTS = (BASINS[a.basin][k] for k in ("bbox", "gauges", "rain_pts"))
    os.makedirs(a.out, exist_ok=True)
    for step in a.only.split(","):
        print("==", step, flush=True)
        {"discharge": fetch_discharge, "rain": fetch_rain, "osm": fetch_osm, "buildings": fetch_buildings,
         "rasters": fetch_rasters, "jrc": fetch_jrc}[step](a.out)
    print("CONTEXT_DONE", flush=True)
