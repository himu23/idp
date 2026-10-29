#!/usr/bin/env python3
"""Find the biggest flood dates for any Indian area from Microsoft's AI4G global SAR flood dataset (2014-2024).
Usage: python3 06_find_flood_dates_ai4g.py --tile N18E084 --bbox 85.3 19.8 87.0 21.0 --out flood_dates.csv
Tile = 3x3 degree cell named by its south-west corner (N18E084 covers 18-21N, 84-87E).
Downloads the tile's post-processing.parquet (~130 MB), counts flood-detected pixels per Sentinel-1 date inside bbox.
These are MODEL detections (not ground truth): use them to choose event dates, then pull imagery with 04_pull_india_s1s2.py.
"""
import argparse, os, urllib.request
import pyarrow.parquet as pq, pyarrow.compute as pc
ap = argparse.ArgumentParser(); ap.add_argument('--tile', required=True); ap.add_argument('--bbox', nargs=4, type=float, required=True)
ap.add_argument('--out', default='flood_dates.csv'); a = ap.parse_args()
fn = f'{a.tile}-post-processing.parquet'
if not os.path.exists(fn):
    urllib.request.urlretrieve(f'https://huggingface.co/datasets/ai-for-good-lab/ai4g-flood-dataset/resolve/main/{a.tile[:3]}/{a.tile}/{fn}', fn)
t = pq.read_table(fn, columns=['year', 'month', 'day', 'lat', 'lon', 'filename'])
W, S, E, N = a.bbox
m = pc.and_(pc.and_(pc.greater_equal(t['lon'], W), pc.less_equal(t['lon'], E)), pc.and_(pc.greater_equal(t['lat'], S), pc.less_equal(t['lat'], N)))
g = t.filter(m).group_by(['year', 'month', 'day']).aggregate([('lat', 'count'), ('filename', 'min')]).to_pandas()
g['date'] = g.apply(lambda r: f"{int(r.year)}-{int(r.month):02d}-{int(r.day):02d}", axis=1)
g = g.sort_values('lat_count', ascending=False).rename(columns={'lat_count': 'flood_pixels_detected', 'filename_min': 'example_s1_scene'})
g[['date', 'flood_pixels_detected', 'example_s1_scene']].to_csv(a.out, index=False)
print(g[['date', 'flood_pixels_detected']].head(15).to_string(index=False))
