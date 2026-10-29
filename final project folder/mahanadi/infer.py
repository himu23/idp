"""Mahanadi delta case study: map water and flood extent for real events with trained models.

    python mahanadi/infer.py <code_dir> <run_dir> [<run_dir> ...]

Inputs (from pull_events.sh, Microsoft Planetary Computer):
  data/mahanadi/<tag>_<date>/s1_vv_vh_db.tif   Sentinel-1 RTC gamma0 in dB (VV, VH), 10 m UTM grid
  data/mahanadi/<tag>_<date>/jrc_occurrence.tif JRC surface-water occurrence 1984-2021 (%)
Models: runs trained on Sen1Floods11 with --save_ckpt (radar-only runs are used because the
monsoon optical images are 61-90 % cloud).

Flood water = water on the event date AND NOT water on the dry-season reference AND JRC
occurrence < 50 % (i.e. not a normal river/lake). Pixel area is exactly 100 m^2 (UTM 10 m grid).

Caveats written into the outputs: Sen1Floods11 radar is GRD sigma0 (GEE) while these pulls are
RTC gamma0; we convert with sigma0 ~= gamma0 + 10 log10(cos 37 deg) = gamma0 - 0.97 dB. There is no
ground truth here (NDEM polygons were not available on the server), so these maps are a
demonstration of the workflow, not a validated product.
"""
import glob
import json
import os
import sys

import numpy as np
import rasterio

sys.path.insert(0, sys.argv[1])
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from radar_model import GAMMA_TO_SIGMA_DB, HOME, load_model, predict_scene  # noqa: E402

DATA = f"{HOME}/data/mahanadi"
OUT = f"{HOME}/runs/_mahanadi"
os.makedirs(OUT, exist_ok=True)
# Dry-season reference: 11 Mar 2020, same descending track (00:05 UTC) and footprint as all three
# event scenes (71 % of the AOI). The 2021 dry scene is from another track and covers only 51 %.
EVENTS = {"event_20220816": "dry2020_20200310", "event_20210529": "dry2020_20200310",
          "event_20200826": "dry2020_20200310"}


def read_s1(tag):
    with rasterio.open(f"{DATA}/{tag}/s1_vv_vh_db.tif") as src:
        return src.read().astype(np.float32) + GAMMA_TO_SIGMA_DB, src.profile


models = [load_model(d) for d in sys.argv[2:]]
summary = {"gamma_to_sigma_db": GAMMA_TO_SIGMA_DB, "events": {}}
cache = {}
for event, dry in EVENTS.items():
    if not os.path.exists(f"{DATA}/{event}/s1_vv_vh_db.tif"):
        print("missing", event)
        continue
    s1_ev, prof = read_s1(event)
    s1_dry, prof_dry = read_s1(dry)
    assert prof["transform"] == prof_dry["transform"] and s1_ev.shape == s1_dry.shape, "grids differ"
    jrc_path = glob.glob(f"{DATA}/{event}/jrc_occurrence.tif") or glob.glob(f"{DATA}/{dry}/jrc_occurrence.tif")
    with rasterio.open(jrc_path[0]) as src:
        jrc = src.read(1).astype(np.float32)
    ev_sum = {}
    for model, norm, name in models:
        key = (name, dry)
        if key not in cache:
            cache[key] = predict_scene(model, norm, s1_dry)
        p_dry = cache[key]
        p_ev = predict_scene(model, norm, s1_ev)
        valid = np.isfinite(p_ev) & np.isfinite(p_dry)
        water_ev = valid & (p_ev >= 0.5)
        water_dry = valid & (p_dry >= 0.5)
        flood = water_ev & ~water_dry & (jrc < 50)
        km2 = lambda m: float(m.sum()) * 100 / 1e6  # noqa: E731
        ev_sum[name] = {"water_event_km2": km2(water_ev), "water_dry_km2": km2(water_dry),
                        "flood_km2": km2(flood), "valid_km2": km2(valid),
                        "permanent_jrc50_km2": km2(valid & (jrc >= 50))}
        p = dict(prof, count=1, dtype="uint8", nodata=255, compress="deflate")
        with rasterio.open(f"{OUT}/{event}_{name}_water_prob.tif", "w", **p) as dst:
            dst.write(np.where(valid, np.round(np.nan_to_num(p_ev) * 254), 255).astype(np.uint8), 1)
        cls = np.zeros(p_ev.shape, np.uint8)  # 0 dry, 1 permanent/normal water, 2 flood, 255 nodata
        cls[water_ev & ~flood] = 1
        cls[flood] = 2
        cls[~valid] = 255
        with rasterio.open(f"{OUT}/{event}_{name}_classes.tif", "w", **p) as dst:
            dst.write(cls, 1)
            dst.update_tags(classes="0 dry, 1 normal/permanent water, 2 flood water, 255 no data")
        print(event, name, json.dumps(ev_sum[name]), flush=True)
    # Otsu on VH as the classical reference (same flood rule)
    from skimage.filters import threshold_otsu
    vh_e, vh_d = s1_ev[1], s1_dry[1]
    ok = np.isfinite(vh_e) & np.isfinite(vh_d)
    te, td = threshold_otsu(vh_e[ok]), threshold_otsu(vh_d[ok])
    fl = ok & (vh_e < te) & ~(vh_d < td) & (jrc < 50)
    ev_sum["otsu_vh"] = {"water_event_km2": float((ok & (vh_e < te)).sum()) / 1e4, "flood_km2": float(fl.sum()) / 1e4,
                         "thr_event_db": float(te), "thr_dry_db": float(td)}
    summary["events"][event] = {"dry_reference": dry, "models": ev_sum,
                                "bounds_utm": list(rasterio.open(f"{DATA}/{event}/s1_vv_vh_db.tif").bounds),
                                "crs": str(prof["crs"])}
json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=1)
print("written", OUT)
