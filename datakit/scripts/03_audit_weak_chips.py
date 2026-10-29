#!/usr/bin/env python3
"""Audit Sen1Floods11 weakly-labelled chips (e.g. the 467 India chips).
Usage: python3 03_audit_weak_chips.py <weak_dir> <hand_manifest.csv> <out.csv>
Labels: S1OtsuLabelWeak = water from a radar (VH) Otsu threshold; S2IndexLabelWeak = water from optical
(NDWI/MNDWI-type) index thresholds. Both are automatic -> fine for extra TRAINING, never for testing.
"""
import sys, os, glob, csv
import numpy as np, rasterio
wd, hand_csv, out = sys.argv[1:4]
hand = list(csv.DictReader(open(hand_csv)))
hb = [(float(r['west']), float(r['south']), float(r['east']), float(r['north']), r['chip'], r['split']) for r in hand]
rows = []
for f in sorted(glob.glob(os.path.join(wd, 'S1OtsuLabelWeak', '*.tif'))):
    chip = os.path.basename(f).replace('_S1OtsuLabelWeak.tif', '')
    with rasterio.open(f) as s:
        o = s.read(1); b = s.bounds
    g = os.path.join(wd, 'S2IndexLabelWeak', chip + '_S2IndexLabelWeak.tif')
    s2l = rasterio.open(g).read(1) if os.path.exists(g) else None
    ok = o >= 0
    r = dict(chip=chip, country=chip.split('_')[0], west=round(b.left, 5), south=round(b.bottom, 5), east=round(b.right, 5), north=round(b.top, 5),
             s1otsu_valid_frac=round(ok.mean(), 4), s1otsu_water_frac=round((o == 1)[ok].mean(), 4) if ok.any() else '')
    if s2l is not None:
        ok2 = s2l >= 0; both = ok & ok2
        r['s2index_valid_frac'] = round(ok2.mean(), 4)
        r['s2index_water_frac'] = round((s2l == 1)[ok2].mean(), 4) if ok2.any() else ''
        inter = ((o == 1) & (s2l == 1) & both).sum(); uni = (((o == 1) | (s2l == 1)) & both).sum()
        r['s1_vs_s2_label_iou'] = round(inter / uni, 4) if uni else ''
    # does this weak chip overlap a hand-labelled chip? (leakage check)
    ov = [h for h in hb if not (h[2] <= b.left or h[0] >= b.right or h[3] <= b.bottom or h[1] >= b.top)]
    r['overlaps_hand_chip'] = ';'.join(f'{h[4]}({h[5]})' for h in ov)
    rows.append(r)
keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
with open(out, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
n = len(rows); ov = sum(bool(r['overlaps_hand_chip']) for r in rows)
wf = [r['s1otsu_water_frac'] for r in rows if r['s1otsu_water_frac'] != '']
io = [r['s1_vs_s2_label_iou'] for r in rows if r.get('s1_vs_s2_label_iou', '') != '']
print(f'weak chips: {n}; overlapping a hand-labelled chip: {ov}')
print(f'radar-label water fraction: mean {np.mean(wf):.3f}, chips with >1% water: {sum(x > 0.01 for x in wf)}')
print(f'agreement radar-label vs optical-label (IoU): median {np.median(io):.2f}')
