#!/usr/bin/env python3
"""Pull co-registered Sentinel-1 + Sentinel-2 (+ JRC surface-water reference) for ONE Indian flood
event from Microsoft Planetary Computer. No account / login needed.

Example (Mahanadi delta, Odisha, 16-21 Aug 2022 flood):
  python3 04_pull_india_s1s2.py --bbox 86.05 20.30 86.20 20.45 --date 2022-08-16 --days 3 --out ../data/india_new/mahanadi_20220816

Outputs (all on ONE common 10 m UTM grid, so they line up pixel-for-pixel):
  s1_vv_vh_db.tif    Sentinel-1 RTC backscatter, 2 bands (VV, VH) in dB         [radar, sees through cloud]
  s2_l2a_12band.tif  Sentinel-2 L2A, 12 bands B01..B12 (no B10), reflectance x10000
  s2_scl.tif         Sentinel-2 scene classification (cloud / shadow / water flags)
  jrc_occurrence.tif JRC Global Surface Water occurrence 0-100 % (1984-2021) = where rivers/lakes normally are
  meta.json          scene IDs, dates, cloud %, time gap between S1 and S2
  preview.png        quick-look figure
"""
import argparse, json, os, sys
import numpy as np
import planetary_computer as pc
import pystac_client, rasterio
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from pyproj import Transformer
from datetime import datetime, timedelta

ap = argparse.ArgumentParser()
ap.add_argument('--bbox', nargs=4, type=float, required=True, metavar=('W', 'S', 'E', 'N'))
ap.add_argument('--date', required=True, help='flood date YYYY-MM-DD (e.g. from NDEM map or AI4G flood list)')
ap.add_argument('--days', type=int, default=3, help='search window +/- days')
ap.add_argument('--res', type=float, default=10.0)
ap.add_argument('--out', required=True)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
W, S, E, N = a.bbox
t0 = datetime.fromisoformat(a.date)
win = f"{(t0 - timedelta(days=a.days)).date()}/{(t0 + timedelta(days=a.days)).date()}"
cat = pystac_client.Client.open('https://planetarycomputer.microsoft.com/api/stac/v1', modifier=pc.sign_inplace)

# ---- common grid: UTM zone of the AOI centre, fixed pixel size
lon0, lat0 = (W + E) / 2, (S + N) / 2
epsg = 32600 + int((lon0 + 180) // 6) + 1 if lat0 >= 0 else 32700 + int((lon0 + 180) // 6) + 1
tf = Transformer.from_crs(4326, epsg, always_xy=True)
xs, ys = zip(*[tf.transform(x, y) for x, y in [(W, S), (W, N), (E, S), (E, N)]])
x0, y1 = np.floor(min(xs) / a.res) * a.res, np.ceil(max(ys) / a.res) * a.res
width, height = int(np.ceil((max(xs) - x0) / a.res)), int(np.ceil((y1 - min(ys)) / a.res))
transform = from_origin(x0, y1, a.res, a.res)
grid = dict(crs=f'EPSG:{epsg}', transform=transform, width=width, height=height)
print(f'grid EPSG:{epsg} {width}x{height} px at {a.res} m')

def read(href, resampling=Resampling.bilinear, dtype='float32'):
    with rasterio.open(href) as src, WarpedVRT(src, resampling=resampling, **grid) as v:
        return v.read(1, out_dtype=dtype)

def save(path, arrs, dtype, names, nodata=None):
    with rasterio.open(path, 'w', driver='GTiff', count=len(arrs), dtype=dtype, compress='deflate',
                       nodata=nodata, **grid) as dst:
        for i, (ar, nm) in enumerate(zip(arrs, names), 1):
            dst.write(ar.astype(dtype), i); dst.set_band_description(i, nm)

meta = {'bbox': a.bbox, 'flood_date': a.date, 'window': win, 'grid_epsg': epsg, 'res_m': a.res}

# ---- Sentinel-1 RTC (gamma0, terrain-corrected) closest in time to the flood date
s1 = list(cat.search(collections=['sentinel-1-rtc'], bbox=a.bbox, datetime=win).items())
if not s1:
    sys.exit('no Sentinel-1 RTC scene in window')
s1.sort(key=lambda it: abs((it.datetime.replace(tzinfo=None) - t0).total_seconds()))
it1 = s1[0]
vv = read(it1.assets['vv'].href); vh = read(it1.assets['vh'].href)
bad = (vv <= 0) | (vh <= 0)
vv_db = np.where(bad, np.nan, 10 * np.log10(np.maximum(vv, 1e-6)))
vh_db = np.where(bad, np.nan, 10 * np.log10(np.maximum(vh, 1e-6)))
save(f'{a.out}/s1_vv_vh_db.tif', [vv_db, vh_db], 'float32', ['VV_dB', 'VH_dB'], nodata=np.nan)
meta['s1'] = dict(id=it1.id, datetime=str(it1.datetime), orbit=it1.properties.get('sat:orbit_state'),
                  candidates=len(s1), invalid_frac=float(bad.mean()))
print('S1 :', it1.id, it1.datetime)

# ---- Sentinel-2 L2A: least cloudy over the AOI within the window
s2 = list(cat.search(collections=['sentinel-2-l2a'], bbox=a.bbox, datetime=win).items())
best = None
for it in sorted(s2, key=lambda i: i.properties.get('eo:cloud_cover', 100))[:6]:
    scl = read(it.assets['SCL'].href, Resampling.nearest, 'uint8')
    valid = (scl > 0)
    cloud = np.isin(scl, [3, 8, 9, 10])  # shadow, cloud medium/high, cirrus
    cf = float(cloud[valid].mean()) if valid.any() else 1.0
    cov = float(valid.mean())
    print(f'   S2 candidate {it.id} tile-cloud={it.properties.get("eo:cloud_cover"):.0f}% AOI-cloud={cf:.0%} coverage={cov:.0%}')
    if cov > 0.5 and (best is None or cf < best[1]):
        best = (it, cf, scl)
if best:
    it2, cf, scl = best
    bands = ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B09', 'B11', 'B12']
    arr = [read(it2.assets[b].href, dtype='float32') for b in bands]
    save(f'{a.out}/s2_l2a_12band.tif', arr, 'uint16', bands, nodata=0)
    save(f'{a.out}/s2_scl.tif', [scl], 'uint8', ['SCL'], nodata=0)
    gap_h = abs((it2.datetime - it1.datetime).total_seconds()) / 3600
    meta['s2'] = dict(id=it2.id, datetime=str(it2.datetime), aoi_cloud_frac=cf, tile_cloud_pct=it2.properties.get('eo:cloud_cover'),
                      s1_s2_gap_hours=round(gap_h, 1), candidates=len(s2))
    print('S2 :', it2.id, f'AOI cloud {cf:.0%}, gap to S1 {gap_h:.1f} h')
else:
    meta['s2'] = None; print('no usable S2 in window')

# ---- JRC Global Surface Water occurrence = where water normally is (rivers, lakes, reservoirs)
jrc = list(cat.search(collections=['jrc-gsw'], bbox=a.bbox).items())
if jrc:
    occ = np.zeros((height, width), 'float32')
    for it in jrc:
        o = read(it.assets['occurrence'].href, Resampling.nearest, 'float32'); occ = np.maximum(occ, np.where(o > 100, 0, o))
    save(f'{a.out}/jrc_occurrence.tif', [occ], 'uint8', ['occurrence_pct'])
    meta['jrc_items'] = [i.id for i in jrc]

# ---- quick weak water mask from radar (VH threshold) -- for a first look ONLY, not ground truth
vhv = vh_db[np.isfinite(vh_db)]
from skimage.filters import threshold_otsu
thr = float(threshold_otsu(vhv)) if vhv.size else -20.0
water = np.isfinite(vh_db) & (vh_db < thr)
meta['vh_otsu_threshold_db'] = round(thr, 2); meta['radar_water_frac'] = round(float(water.mean()), 4)
if jrc:
    perm = occ >= 75
    meta['jrc_perm_water_frac'] = round(float(perm.mean()), 4)
    meta['radar_water_outside_perm_frac'] = round(float((water & ~perm).mean()), 4)
json.dump(meta, open(f'{a.out}/meta.json', 'w'), indent=2, default=str)

# ---- preview
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig, ax = plt.subplots(1, 4, figsize=(18, 5))
if best:
    rgb = np.dstack([arr[3], arr[2], arr[1]]); rgb = np.clip(rgb / 3000, 0, 1)
    ax[0].imshow(rgb); ax[0].set_title(f'Sentinel-2 L2A RGB\n{str(it2.datetime)[:16]}  AOI cloud {cf:.0%}')
else:
    ax[0].set_title('no Sentinel-2')
ax[1].imshow(np.clip(vh_db, -28, -8), cmap='gray'); ax[1].set_title(f'Sentinel-1 RTC VH (dB)\n{str(it1.datetime)[:16]}')
ax[2].imshow(water, cmap='Blues'); ax[2].set_title(f'Radar water (VH < {thr:.1f} dB)\n{water.mean():.0%} of AOI')
if jrc:
    ax[3].imshow(occ, cmap='Blues', vmin=0, vmax=100); ax[3].set_title('JRC normal water occurrence (%)\n(rivers / lakes reference)')
for x in ax: x.set_xticks([]); x.set_yticks([])
plt.suptitle(f'{a.out.rstrip("/").split("/")[-1]}  bbox={a.bbox}', y=1.02)
plt.tight_layout(); plt.savefig(f'{a.out}/preview.png', dpi=110, bbox_inches='tight')
print(json.dumps(meta, indent=1, default=str))
