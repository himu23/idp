"""Independent check of the radar water maps in the project area: Sentinel-2 optical water within +/- 1 day.

    python mahanadi/s2_crosscheck.py --prob <runs/_atlas/prob> --inventory <inventory.csv> --normal <normal_water_latest.tif> --out <dir>

There is no surveyed flood map for the Mahanadi delta, so the radar atlas model (mean of the radar-only
TerraMind-B and U-Net, at the atlas threshold) is compared
with a different sensor: Sentinel-2 L2A on clear pixels (scene classification 4/5/6 = vegetation, bare, water),
optical water = MNDWI = (B03 - B11)/(B03 + B11) > 0 (Xu 2006). Both on the 20 m atlas grid. Reported for all
water and for water outside the normal-water mask (the flood part). Processing baseline >= 04.00 (from 25 Jan 2022)
carries a +1000 offset on L2A reflectance, which is removed.
Outputs: s2_pairs.csv (one row per radar/optical pair), s2_crosscheck.json (pooled scores)
"""
import argparse
import collections
import json
import os

import numpy as np
import pandas as pd
import planetary_computer as pc
import pystac_client
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

os.environ.setdefault("GDAL_NUM_THREADS", "8")
os.environ.setdefault("CPL_VSIL_CURL_CHUNK_SIZE", "2097152")
os.environ.setdefault("GDAL_HTTP_MULTIRANGE", "YES")
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")

from basins import BASINS  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--prob", required=True)
ap.add_argument("--inventory", required=True, nargs="+")
ap.add_argument("--normal", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--models", default="terramind,unet", help="water probability = mean of these models' maps")
ap.add_argument("--thr", type=float, default=0.5)
ap.add_argument("--min_clear", type=float, default=0.3)
ap.add_argument("--max_pairs", type=int, default=60, help="monsoon/post-monsoon pairs first, then dry season")
ap.add_argument("--basin", default="mahanadi", help="key of basins.py (the search box)")
a = ap.parse_args()
BBOX = BASINS[a.basin]["bbox"]
os.makedirs(a.out, exist_ok=True)

with rasterio.open(a.normal) as src:
    grid = dict(crs=src.crs, transform=src.transform, width=src.width, height=src.height)
    normal = src.read(1).astype(bool)
inv = pd.concat([pd.read_csv(f) for f in a.inventory]).drop_duplicates("name")
MODELS = a.models.split(",")
inv = inv[[all(os.path.exists(f"{a.prob}/{n}_{m}.tif") for m in MODELS) for n in inv.name]]
inv["date"] = pd.to_datetime(inv.date)

cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
s2 = list(cat.search(collections=["sentinel-2-l2a"], bbox=BBOX, datetime="2017-01-01/2026-10-27",
                     query={"eo:cloud_cover": {"lt": 40}}).items())
by_day = collections.defaultdict(list)
for it in s2:
    by_day[it.datetime.date()].append(it)
print(len(s2), "S2 items with < 40 % tile cloud on", len(by_day), "days", flush=True)


def warp(href, resampling, dtype, overview=False):
    """On the 20 m grid; 10 m bands are read from their 20 m overview (4x less data on a slow link)."""
    with rasterio.open(href, **({"overview_level": 0} if overview else {})) as src,             WarpedVRT(src, resampling=resampling, **grid) as v:
        return v.read(1, out_dtype=dtype)


def optical(items):
    """Mosaic of the day's tiles on the 20 m grid: (water, clear) booleans. The scene classification is read
    first; days with too little clear land are dropped before the reflectance bands are downloaded."""
    water = np.zeros((grid["height"], grid["width"]), bool)
    clear = np.zeros_like(water)
    oks = []
    for it in items:
        it = pc.sign(it)
        scl = warp(it.assets["SCL"].href, Resampling.nearest, "uint8")
        ok = np.isin(scl, [4, 5, 6]) & ~clear
        clear |= ok
        oks.append((it, ok))
    if clear.mean() < a.min_clear:
        return water, clear
    for it, ok in oks:
        if not ok.any():
            continue
        off = 1000 if str(it.properties.get("s2:processing_baseline", "0")) >= "04.00" else 0
        g_ = warp(it.assets["B03"].href, Resampling.bilinear, "float32", overview=True) - off
        s_ = warp(it.assets["B11"].href, Resampling.bilinear, "float32") - off
        mndwi = (g_ - s_) / np.maximum(g_ + s_, 1)
        water[ok] = mndwi[ok] > 0
    return water, clear


def edge_band(nod, px=150):
    """Same 3 km swath-edge buffer as the atlas."""
    from scipy import ndimage
    if not nod.any():
        return np.zeros_like(nod)
    d = ndimage.distance_transform_edt(~nod[::5, ::5]) * 5
    return np.repeat(np.repeat(d, 5, 0), 5, 1)[:nod.shape[0], :nod.shape[1]] <= px


cands = []
for _, p in inv.iterrows():
    days = [p.date.date() + pd.Timedelta(days=k) for k in (0, -1, 1)]
    day = next((d for d in days if d in by_day), None)
    if day is not None:
        cands.append((0 if p.date.month in (6, 7, 8, 9, 10, 11) else 1, p.date, p, day))
cands.sort(key=lambda c: (c[0], c[1]))
print(len(cands), "radar passes with a Sentinel-2 image within a day; checking up to", a.max_pairs, flush=True)
rows = []
for _, _, p, day in cands:
    if len(rows) >= a.max_pairs:
        break
    try:
        ow, clear = optical(by_day[day])
    except Exception as ex:
        print("skip", p["name"], repr(ex)[:100], flush=True)
        continue
    prs = []
    for m in MODELS:
        with rasterio.open(f"{a.prob}/{p['name']}_{m}.tif") as src:
            prs.append(src.read(1))
    nod = np.any([q == 255 for q in prs], axis=0)
    nod = nod | edge_band(nod)
    pr = np.mean([q.astype(np.float32) for q in prs], axis=0)
    both = clear & ~nod
    if both.mean() < a.min_clear:
        continue
    rw = pr >= a.thr * 254
    rec = dict(s1=p["name"], s2_date=str(day), gap_days=(pd.Timestamp(day) - p.date.normalize()).days,
               month=int(p.date.month), compared_km2=round(both.sum() * 400 / 1e6, 1))
    for tag, m in (("all", both), ("outside_normal", both & ~normal)):
        tp, fp, fn = int((rw & ow & m).sum()), int((rw & ~ow & m).sum()), int((~rw & ow & m).sum())
        rec.update({f"{tag}_tp": tp, f"{tag}_fp": fp, f"{tag}_fn": fn,
                    f"{tag}_iou": round(tp / max(tp + fp + fn, 1), 3),
                    f"{tag}_optical_water_km2": round((ow & m).sum() * 400 / 1e6, 1),
                    f"{tag}_radar_water_km2": round((rw & m).sum() * 400 / 1e6, 1)})
    rows.append(rec)
    print(rec["s1"], rec["s2_date"], rec["compared_km2"], "km2  IoU all", rec["all_iou"], "outside normal",
          rec["outside_normal_iou"], flush=True)

df = pd.DataFrame(rows)
df.to_csv(f"{a.out}/s2_pairs.csv", index=False)
out = {"pairs": len(df)}
for tag in ("all", "outside_normal"):
    for season, sub in (("all_months", df), ("monsoon_Jun_Nov", df[df.month.isin([6, 7, 8, 9, 10, 11])]),
                        ("dry_Feb_Mar", df[df.month.isin([2, 3])])):
        tp, fp, fn = sub[f"{tag}_tp"].sum(), sub[f"{tag}_fp"].sum(), sub[f"{tag}_fn"].sum()
        out[f"{tag}/{season}"] = dict(pairs=len(sub), iou=round(tp / max(tp + fp + fn, 1), 3),
                                      precision=round(tp / max(tp + fp, 1), 3), recall=round(tp / max(tp + fn, 1), 3))
json.dump(out, open(f"{a.out}/s2_crosscheck.json", "w"), indent=1)
print(json.dumps(out, indent=1))
print("S2_CROSSCHECK_DONE")
