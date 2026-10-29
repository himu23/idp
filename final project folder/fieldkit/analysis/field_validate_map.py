"""Check the satellite flood atlas against what was seen and heard at the field points.

    python fieldkit/analysis/field_validate_map.py <ground_truth_points.csv> <atlas_dir>

ground_truth_points.csv: point_id, lat, lon, flooded_in_years_local_report ("2020;2022", or "none" when the
informant is sure the spot did not flood in the atlas years), flood_mark_height_above_ground_m, ...
atlas_dir: flood_frequency.tif, max_extent_by_year.tif (one band per year), trigger_discharge.tif (20 m grid).

Every (point, atlas year) pair with a local answer is one test: hit (both say flooded), miss (people say flooded,
atlas does not), false alarm (atlas says flooded, people say not), correct negative. A 3 x 3 pixel window (60 m)
absorbs GPS error. Scores: probability of detection POD = hits / (hits + misses), false-alarm ratio
FAR = false alarms / (hits + false alarms), critical success index CSI = hits / (hits + misses + false alarms).
Local memory is itself uncertain (dates, extent), so the table keeps every pair for discussion.
"""
import json
import sys

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from scipy import ndimage

pts = pd.read_csv(sys.argv[1])
d = sys.argv[2].rstrip("/")
with rasterio.open(f"{d}/max_extent_by_year.tif") as src:
    ext = src.read().astype(bool)
    years = [int(y) for y in src.tags()["description"].split("= ")[1].split(",")]
    t, crs = src.transform, src.crs
with rasterio.open(f"{d}/flood_frequency.tif") as src:
    freq = src.read(1)
with rasterio.open(f"{d}/trigger_discharge.tif") as src:
    theta = src.read(1)
ext3 = np.stack([ndimage.maximum_filter(e, 3) for e in ext])
x, y = Transformer.from_crs(4326, crs, always_xy=True).transform(pts.lon.values, pts.lat.values)
c = np.floor((x - t.c) / t.a).astype(int)
r = np.floor((t.f - y) / -t.e).astype(int)
inside = (r >= 0) & (r < freq.shape[0]) & (c >= 0) & (c < freq.shape[1])
rows, pairs = [], []
for i, p in pts.iterrows():
    if not inside[i]:
        continue
    rec = dict(point_id=p.point_id, atlas_flood_freq_pct=None if freq[r[i], c[i]] == 255 else int(freq[r[i], c[i]]),
               atlas_trigger_Q=float(theta[r[i], c[i]]),
               atlas_years_flooded=";".join(str(yy) for yy, e in zip(years, ext3) if e[r[i], c[i]]))
    rep = str(p.get("flooded_in_years_local_report", "")).strip().lower()
    if rep and rep != "nan":
        local = set() if rep == "none" else {int(v) for v in rep.replace(",", ";").split(";") if v.strip().isdigit()}
        for yy, e in zip(years, ext3):
            sat, loc = bool(e[r[i], c[i]]), yy in local
            pairs.append(dict(point_id=p.point_id, year=yy, local=loc, atlas=sat))
    rows.append(rec)
out = pts.merge(pd.DataFrame(rows), on="point_id", how="left")
out.to_csv(sys.argv[1].replace(".csv", "_vs_atlas.csv"), index=False)
pr = pd.DataFrame(pairs)
if len(pr):
    h = int((pr.local & pr.atlas).sum())
    m = int((pr.local & ~pr.atlas).sum())
    fa = int((~pr.local & pr.atlas).sum())
    cn = int((~pr.local & ~pr.atlas).sum())
    s = dict(points=int(inside.sum()), pairs=len(pr), hits=h, misses=m, false_alarms=fa, correct_negatives=cn,
             POD=round(h / max(h + m, 1), 3), FAR=round(fa / max(h + fa, 1), 3), CSI=round(h / max(h + m + fa, 1), 3))
    pr.to_csv(sys.argv[1].replace(".csv", "_pairs.csv"), index=False)
    print(json.dumps(s, indent=1))
print(out[["point_id", "flooded_in_years_local_report", "atlas_years_flooded", "atlas_flood_freq_pct"]].to_string(index=False))
