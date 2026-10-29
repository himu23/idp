#!/usr/bin/env python3
"""Audit the Sen1Floods11 v1.1 hand-labelled package (the same data Flood_AI.ipynb uses).

Usage:  python3 02_audit_sen1floods11.py <path/to/sen1floods11_v1.1> <output_dir> [metadata.geojson]

Writes:
  sen1floods11_handlabeled_manifest.csv  one row per chip (446)
  sen1floods11_summary_by_country.csv    totals per country/event
  sen1floods11_india_chips.csv           the India (Assam, 12 Aug 2016) subset
Prints the key checks: does the hand label include permanent rivers/lakes (all surface water)?
"""
import sys, os, glob, csv, json
import numpy as np, rasterio

root, out = sys.argv[1], sys.argv[2]
meta_path = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(out, exist_ok=True)
D = os.path.join(root, 'data')

# split membership
split_of = {}
for name, fn in [('train', 'flood_train_data.txt'), ('val', 'flood_valid_data.txt'),
                 ('test', 'flood_test_data.txt'), ('bolivia_holdout', 'flood_bolivia_data.txt')]:
    p = os.path.join(root, 'splits', fn)
    if not os.path.exists(p):
        continue
    for line in open(p):
        line = line.strip()
        if not line:
            continue
        stem = os.path.basename(line.split(',')[0]).split('.')[0]
        for suf in ('_S1Hand', '_S2Hand', '_LabelHand', '_S1GRDHand', '_S2L1CHand'):
            if stem.endswith(suf):
                stem = stem[:-len(suf)]
        split_of.setdefault(stem, name)  # bolivia chips also appear in test; keep first assignment

# event metadata (dates, orbit) from Sen1Floods11_Metadata.geojson
event = {}
if meta_path and os.path.exists(meta_path):
    for f in json.load(open(meta_path))['features']:
        p = f['properties']
        key = {'Cambodia': 'Mekong'}.get(p['location'], p['location'])
        event[key] = p

rows = []
for lab in sorted(glob.glob(os.path.join(D, 'LabelHand', '*_LabelHand.tif'))):
    chip = os.path.basename(lab).replace('_LabelHand.tif', '')
    country = chip.split('_')[0]
    f = lambda prod, suf: os.path.join(D, prod, f'{chip}_{suf}.tif')
    with rasterio.open(lab) as s:
        y = s.read(1); b = s.bounds
    with rasterio.open(f('JRCWaterHand', 'JRCWaterHand')) as s:
        jrc = s.read(1)
    with rasterio.open(f('S1OtsuLabelHand', 'S1OtsuLabelHand')) as s:
        otsu = s.read(1)
    with rasterio.open(f('S1GRDHand', 'S1Hand')) as s:
        s1 = s.read().astype('float32')
    with rasterio.open(f('S2L1CHand', 'S2Hand')) as s:
        s2 = s.read()
    dem_p = f('CopernicusDEM', 'DEM')
    dem = rasterio.open(dem_p).read(1) if os.path.exists(dem_p) else None

    lab_ok = y >= 0
    n = y.size
    water = (y == 1); dry = (y == 0)
    perm = (jrc == 1)
    s1_bad = ~np.isfinite(s1).all(0) | (s1 < -80).any(0)
    s2_bad = (s2 == 0).all(0)
    # agreement of Sen1Floods11's own S1 Otsu weak label with the hand label
    o_ok = lab_ok & (otsu >= 0)
    tp = int(((otsu == 1) & water & o_ok).sum()); fp = int(((otsu == 1) & dry & o_ok).sum()); fn_ = int(((otsu == 0) & water & o_ok).sum())
    vv, vh = s1[0], s1[1]
    good = lab_ok & ~s1_bad
    med = lambda a, m: float(np.median(a[m])) if m.sum() > 50 else np.nan
    ev = event.get(country, {})
    rows.append(dict(
        chip=chip, country=country, split=split_of.get(chip, 'unassigned'),
        s1_date=ev.get('s1_date', ''), s2_date=ev.get('s2_date', ''), orbit=ev.get('orbit', ''),
        west=round(b.left, 5), south=round(b.bottom, 5), east=round(b.right, 5), north=round(b.top, 5),
        lon=round((b.left + b.right) / 2, 5), lat=round((b.bottom + b.top) / 2, 5),
        labelled_frac=round(lab_ok.mean(), 4), unlabelled_frac=round(1 - lab_ok.mean(), 4),
        water_frac_of_labelled=round(water.sum() / max(lab_ok.sum(), 1), 4),
        water_px=int(water.sum()), dry_px=int(dry.sum()),
        jrc_perm_water_frac=round(perm.mean(), 4),
        jrc_perm_px_labelled=int((perm & lab_ok).sum()),
        jrc_perm_labelled_as_water=round((perm & water).sum() / max((perm & lab_ok).sum(), 1), 4) if (perm & lab_ok).sum() > 0 else '',
        event_water_px=int((water & ~perm).sum()),
        perm_water_px=int((water & perm).sum()),
        s1_invalid_frac=round(s1_bad.mean(), 4), s2_nodata_frac=round(s2_bad.mean(), 4),
        otsu_vs_hand_iou=round(tp / max(tp + fp + fn_, 1), 4) if (tp + fp + fn_) > 0 else '',
        vh_median_water_db=round(med(vh, good & water), 2), vh_median_dry_db=round(med(vh, good & dry), 2),
        dem_mean_m=round(float(dem.mean()), 1) if dem is not None else '',
    ))

keys = list(rows[0])
with open(os.path.join(out, 'sen1floods11_handlabeled_manifest.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
with open(os.path.join(out, 'sen1floods11_india_chips.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows([r for r in rows if r['country'] == 'India'])

# per-country summary
summ = []
for c in sorted({r['country'] for r in rows}):
    R = [r for r in rows if r['country'] == c]
    wp = sum(r['water_px'] for r in R); dp = sum(r['dry_px'] for r in R)
    pp = sum(r['perm_water_px'] for r in R); ep = sum(r['event_water_px'] for r in R)
    pl = sum(r['jrc_perm_px_labelled'] for r in R)
    summ.append(dict(country=c, s1_date=R[0]['s1_date'], s2_date=R[0]['s2_date'], chips=len(R),
                     train=sum(r['split'] == 'train' for r in R), val=sum(r['split'] == 'val' for r in R),
                     test=sum(r['split'] == 'test' for r in R), bolivia_holdout=sum(r['split'] == 'bolivia_holdout' for r in R),
                     water_share_of_labelled=round(wp / max(wp + dp, 1), 4),
                     share_of_water_that_is_JRC_permanent=round(pp / max(wp, 1), 4),
                     JRC_permanent_px_labelled_as_water=round(pp / max(pl, 1), 4) if pl else '',
                     mean_unlabelled_frac=round(np.mean([r['unlabelled_frac'] for r in R]), 4),
                     chips_with_water=sum(r['water_px'] > 0 for r in R)))
with open(os.path.join(out, 'sen1floods11_summary_by_country.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(summ[0])); w.writeheader(); w.writerows(summ)

W = sum(r['water_px'] for r in rows); P = sum(r['perm_water_px'] for r in rows)
PL = sum(r['jrc_perm_px_labelled'] for r in rows)
print(f'chips audited: {len(rows)}')
print(f'labelled water pixels: {W:,}  of which inside JRC permanent water: {P:,} ({P/W:.1%})')
print(f'JRC permanent-water pixels (labelled) that the hand label calls WATER: {P/PL:.1%}  -> hand labels include rivers/lakes' if PL else 'no JRC water')
for s in summ:
    print(s)
