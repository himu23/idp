"""Pull every Sentinel-1 RTC pass over the Mahanadi-delta AOI onto one grid (the flood atlas input).

    python mahanadi/atlas_pull.py --out <dir> [--res 20] [--start 2017-01-01] [--end 2026-10-27] [--months 1,2,...]

One file per pass, all slices of the same pass mosaicked: S1_<yyyymmdd>_<A|D><relorbit>.tif, bands VV and VH
in dB x 100 (int16, nodata -32768), plus inventory.csv (one row per pass). The 10 m grid is computed exactly as
in pull_s1s2.py (UTM of the AOI centre), so the JRC layer of the event pulls lines up pixel-for-pixel; the 20 m
atlas grid has the same origin and twice the pixel size.
--res 20 (default) reads the first COG overview, which is the exact 2 x 2 average of the 10 m linear power
(checked against a full-resolution read): 4x less data. From the IITB server Planetary Computer gave only
4-8 MB/s in total, i.e. 4-7 h for the 590 passes at 10 m. The radar models lose ~0.01-0.02 IoU on Sen1Floods11
when fed this 20 m data up-sampled to 10 m (scripts/test_resolution.py).
Source: Microsoft Planetary Computer, collection sentinel-1-rtc (gamma0, terrain corrected); no login needed.
"""
import argparse
import collections
import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import planetary_computer as pc
import pystac_client
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window

# GDAL_NUM_THREADS + 2 MB chunks + multi-range requests: a 10 m AOI window of one band comes down in ~3 s
# instead of ~54 s with the defaults (measured from the IITB server to Planetary Computer, Oct 2026).
os.environ.setdefault("GDAL_NUM_THREADS", "8")  # more threads x workers triggers connection resets
os.environ.setdefault("CPL_VSIL_CURL_CHUNK_SIZE", "2097152")
os.environ.setdefault("GDAL_HTTP_MULTIRANGE", "YES")
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "5")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "3")
# The server's connections are erratic: the same range request ran at 145 kB/s and, retried, at 6 MB/s. A read
# waits for its slowest connection, so a connection slower than 300 kB/s for 15 s is aborted and the band is
# read again on fresh connections (retry loop in pull_pass).
os.environ.setdefault("GDAL_HTTP_CONNECTTIMEOUT", "20")
os.environ.setdefault("GDAL_HTTP_TIMEOUT", "120")
os.environ.setdefault("GDAL_HTTP_LOW_SPEED_TIME", "15")
os.environ.setdefault("GDAL_HTTP_LOW_SPEED_LIMIT", "300000")
NODATA = -32768


def make_grid(bbox, res=10.0):
    W, S, E, N = bbox
    lon0, lat0 = (W + E) / 2, (S + N) / 2
    epsg = (32600 if lat0 >= 0 else 32700) + int((lon0 + 180) // 6) + 1
    tf = Transformer.from_crs(4326, epsg, always_xy=True)
    xs, ys = zip(*[tf.transform(x, y) for x, y in [(W, S), (W, N), (E, S), (E, N)]])
    x0, y1 = np.floor(min(xs) / res) * res, np.ceil(max(ys) / res) * res
    width, height = int(np.ceil((max(xs) - x0) / res)), int(np.ceil((y1 - min(ys)) / res))
    return dict(crs=f"EPSG:{epsg}", transform=from_origin(x0, y1, res, res), width=width, height=height)


def make_grid20(bbox):
    g = make_grid(bbox, 10.0)
    t = g["transform"]
    return dict(crs=g["crs"], transform=from_origin(t.c, t.f, 20.0, 20.0), width=g["width"] // 2,
                height=g["height"] // 2)


def read(href, grid):
    """AOI window of one band on the grid; a plain window read when the scene (or its 2x overview for a 20 m grid)
    is on the same UTM lattice, otherwise a bilinear warp."""
    t = grid["transform"]
    with rasterio.open(href, **({"overview_level": 0} if t.a == 20 else {})) as src:
        st = src.transform
        if (src.crs.to_epsg() == int(grid["crs"].split(":")[1]) and src.res == (t.a, -t.e)
                and (t.c - st.c) % t.a == 0 and (st.f - t.f) % t.a == 0):
            w = Window((t.c - st.c) / t.a, (st.f - t.f) / t.a, grid["width"], grid["height"])
            return src.read(1, window=w, boundless=True, fill_value=0, out_dtype="float32")
        with WarpedVRT(src, resampling=Resampling.bilinear, **grid) as v:
            return v.read(1, out_dtype="float32")


def pull_pass(key, items, grid, out_dir):
    day, orbit_state, rel = key
    name = f"S1_{day.replace('-', '')}_{orbit_state[0].upper()}{rel:03d}"
    path = f"{out_dir}/{name}.tif"
    if os.path.exists(path):
        return None
    t = time.time()
    db = np.full((2, grid["height"], grid["width"]), np.nan, np.float32)
    for it in items:
        for b, pol in enumerate(("vv", "vh")):
            for attempt in range(8):  # dropped / aborted range requests: retry on fresh connections
                try:
                    lin = read(pc.sign(it).assets[pol].href, grid)  # fresh SAS token per read
                    break
                except rasterio.errors.RasterioIOError:
                    if attempt == 7:
                        raise
                    time.sleep(3 + 5 * attempt)
            ok = np.isfinite(lin) & (lin > 0) & np.isnan(db[b])
            db[b][ok] = 10 * np.log10(lin[ok])
    valid = np.isfinite(db).all(0)
    out = np.where(valid, np.clip(np.round(db * 100), -5000, 3000), NODATA).astype(np.int16)
    tmp = path + ".part"
    with rasterio.open(tmp, "w", driver="GTiff", count=2, dtype="int16", nodata=NODATA, compress="deflate",
                       predictor=2, tiled=True, blockxsize=512, blockysize=512, **grid) as dst:
        dst.write(out)
        dst.set_band_description(1, "VV_dB_x100")
        dst.set_band_description(2, "VH_dB_x100")
        dst.update_tags(items=",".join(i.id for i in items), datetime=str(items[0].datetime))
    os.replace(tmp, path)
    p = items[0].properties
    return dict(name=name, date=day, time_utc=str(items[0].datetime)[11:19], platform=p.get("platform", "").lower(),
                orbit_state=orbit_state, relative_orbit=rel, n_slices=len(items),
                coverage=round(float(valid.mean()), 4), seconds=round(time.time() - t, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", nargs=4, type=float, default=[85.80, 20.25, 86.45, 20.65])
    ap.add_argument("--start", default="2017-01-01")
    ap.add_argument("--end", default="2026-10-27")
    ap.add_argument("--months", default="1,2,3,4,5,6,7,8,9,10,11,12")
    ap.add_argument("--min_coverage", type=float, default=0.3)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0, help="pull only the first N passes (throughput test)")
    ap.add_argument("--res", type=int, default=20, choices=[10, 20])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    grid = make_grid20(a.bbox) if a.res == 20 else make_grid(a.bbox)
    months = {int(m) for m in a.months.split(",")}
    cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    items = list(cat.search(collections=["sentinel-1-rtc"], bbox=a.bbox, datetime=f"{a.start}/{a.end}").items())
    passes = collections.defaultdict(list)
    for it in items:
        if it.datetime.month in months:
            p = it.properties
            passes[(str(it.datetime.date()), p["sat:orbit_state"], int(p["sat:relative_orbit"]))].append(it)
    # Peak-monsoon passes of every year first, so a usable year-balanced atlas exists long before the end
    rank = {m: i for i, m in enumerate([8, 9, 7, 10, 2, 3, 6, 11, 1, 4, 5, 12])}
    keys = sorted(passes, key=lambda k: (rank[int(k[0][5:7])], k))
    if a.limit:
        keys = keys[:a.limit]
    print(f"{len(items)} items -> {len(passes)} passes; pulling {len(keys)} with {a.workers} workers", flush=True)
    inv = f"{a.out}/inventory.csv"
    fields = ["name", "date", "time_utc", "platform", "orbit_state", "relative_orbit", "n_slices", "coverage", "seconds"]
    new = not os.path.exists(inv)
    with open(inv, "a", newline="") as f, ThreadPoolExecutor(a.workers) as ex:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        futs = {ex.submit(pull_pass, k, passes[k], grid, a.out): k for k in keys}
        for n, fu in enumerate(as_completed(futs), 1):
            try:
                row = fu.result()
            except Exception as e:  # one bad pass must not stop a multi-hour pull
                print("FAILED", futs[fu], repr(e)[:200], flush=True)
                continue
            if row:
                w.writerow(row)
                f.flush()
                print(f"[{n}/{len(keys)}] {row['name']} cov={row['coverage']:.2f} {row['seconds']}s", flush=True)
    print("ATLAS_PULL_DONE", flush=True)


if __name__ == "__main__":
    main()
