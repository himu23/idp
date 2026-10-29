"""Map water on every pulled Sentinel-1 pass with the radar-only models (flood-atlas step 2).

    python mahanadi/atlas_infer.py <code_dir> <atlas_dir> [<atlas_dir> ...] --out <out_dir> --runs <run_dir> [<run_dir> ...] [--wait]

Every pass goes through the same chain whatever resolution it was pulled at: 20 m linear power (10 m pulls are
averaged 2 x 2, which is exactly how the COG overviews are made) -> bilinear up-sampling to 10 m -> model at 10 m
(the resolution it was trained on) -> water probability averaged back to the 20 m atlas grid.
Output per pass and model: <out_dir>/<pass>_<model>.tif, probability x 254 as uint8 (255 = no radar).
Passes already mapped are skipped, so the script can run while the pull is going; with --wait it keeps polling
until every atlas_pull.py log it watches says ATLAS_PULL_DONE.
"""
import argparse
import glob
import os
import sys
import time

import numpy as np
import rasterio
import torch

ap = argparse.ArgumentParser()
ap.add_argument("code")
ap.add_argument("atlas", nargs="+")
ap.add_argument("--out", required=True)
ap.add_argument("--runs", nargs="+", required=True)
ap.add_argument("--wait", action="store_true")
a = ap.parse_args()
sys.path.insert(0, a.code)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from radar_model import GAMMA_TO_SIGMA_DB, HOME, load_model, predict_scene  # noqa: E402

os.makedirs(a.out, exist_ok=True)
models = [load_model(d) for d in a.runs]


def block2(x):
    H, W = x.shape[-2] // 2 * 2, x.shape[-1] // 2 * 2
    b = x[..., :H, :W].reshape(*x.shape[:-2], H // 2, 2, W // 2, 2)
    with np.errstate(invalid="ignore"), __import__("warnings").catch_warnings():
        __import__("warnings").simplefilter("ignore", RuntimeWarning)
        return np.nanmean(b, axis=(-3, -1))


def run_pass(path):
    name = os.path.basename(path)[:-4]
    todo = [m for m in models if not os.path.exists(f"{a.out}/{name}_{m[2]}.tif")]
    if not todo:
        return 0
    with rasterio.open(path) as src:
        raw, prof, res = src.read(), src.profile, src.res[0]
    lin = np.where(raw == -32768, np.nan, np.power(10.0, raw / 1000.0)).astype(np.float32)  # dB x 100 -> linear
    if res == 10:
        lin = block2(lin)
    t = prof["transform"]
    H20, W20 = lin.shape[1:]
    valid20 = np.isfinite(lin).all(0)
    up = torch.nn.functional.interpolate(torch.from_numpy(np.nan_to_num(lin))[None], scale_factor=2, mode="bilinear",
                                         align_corners=False)[0].numpy()
    s1 = 10 * np.log10(np.maximum(up, 1e-6)) + GAMMA_TO_SIGMA_DB
    s1[:, ~np.repeat(np.repeat(valid20, 2, 0), 2, 1)] = np.nan
    p20 = dict(driver="GTiff", count=1, dtype="uint8", nodata=255, compress="deflate", crs=prof["crs"],
               transform=rasterio.Affine(20.0, 0, t.c, 0, -20.0, t.f), width=W20, height=H20)
    for model, norm, mname in todo:
        prob = block2(predict_scene(model, norm, s1))
        img = np.where(np.isfinite(prob) & valid20, np.round(np.nan_to_num(prob) * 254), 255).astype(np.uint8)
        tmp = f"{a.out}/{name}_{mname}.tif.part"
        with rasterio.open(tmp, "w", **p20) as dst:
            dst.write(img, 1)
        os.replace(tmp, f"{a.out}/{name}_{mname}.tif")
    return len(todo)


while True:
    logs = [open(f"{HOME}/logs/{os.path.basename(d.rstrip('/'))}_pull.log").read() if os.path.exists(
        f"{HOME}/logs/{os.path.basename(d.rstrip('/'))}_pull.log") else "ATLAS_PULL_DONE" for d in a.atlas]
    done_flag = all("ATLAS_PULL_DONE" in s for s in logs) if a.wait else True
    n = 0
    files = {}
    for d in a.atlas:  # a pass pulled at 20 m wins over the same pass pulled at 10 m
        for f in sorted(glob.glob(f"{d}/S1_*.tif")):
            files.setdefault(os.path.basename(f), f)
    for f in files.values():
        t0 = time.time()
        k = run_pass(f)
        if k:
            n += 1
            print(f"{os.path.basename(f)} {k} model(s) {time.time() - t0:.1f}s", flush=True)
    if done_flag and n == 0:
        break
    if n == 0:
        time.sleep(60)
print("ATLAS_INFER_DONE", flush=True)
