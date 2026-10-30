"""Does a radar model trained at 10 m still work on 20 m radar resampled back to 10 m?

    python scripts/test_resolution.py <code_dir> <run_dir> [<run_dir> ...] [--json <out.json>]

The Mahanadi atlas pulls Sentinel-1 from the 20 m COG overviews (4x less data; the 10 m pull was capped at
~4-8 MB/s from the server). This test degrades the Sen1Floods11 official test chips the same way (2 x 2 block
average in linear power, or decimation like a nearest-neighbour overview) and up-samples bilinearly to 10 m,
then compares pooled water IoU at threshold 0.5 with the native 10 m input.
"""
import json
import os
import sys

import numpy as np
import torch

OUT = None
if "--json" in sys.argv:  # optional machine-readable copy of the printed table (runs/_analysis/radar20m*.json)
    k = sys.argv.index("--json")
    OUT = sys.argv[k + 1]
    del sys.argv[k:k + 2]
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, os.path.join(sys.argv[1], "mahanadi"))
from floodfm.data import Cache  # noqa: E402
from radar_model import load_model  # noqa: E402

cache = Cache("/dev/shm/floodfm_cache" if os.path.exists("/dev/shm/floodfm_cache/index.json") else "/home1/vineet/floodfm/data/cache")
test = [cache.pos[c] for c in cache.split("official", "test")]
val = [cache.pos[c] for c in cache.split("official", "val")]


def degrade(s1, how):
    if how == "native":
        return s1
    lin = np.power(10.0, s1 / 10.0)
    if how == "avg20":
        d = np.nanmean(lin.reshape(2, 256, 2, 256, 2), axis=(2, 4))
    else:
        d = lin[:, ::2, ::2]
    up = torch.nn.functional.interpolate(torch.from_numpy(d.astype(np.float32))[None], scale_factor=2,
                                         mode="bilinear", align_corners=False)[0].numpy()
    out = 10 * np.log10(np.maximum(up, 1e-6))
    out[~np.isfinite(s1)] = np.nan
    return out


models = [load_model(run) for run in sys.argv[2:]]
res = {}
for how in ("native", "avg20", "nearest20"):
    probs = {name: [] for _, _, name in models}
    for i in test:
        s1 = degrade(cache.s1[i].astype(np.float32), how)
        for model, norm, name in models:
            x = norm({"S1GRD": torch.from_numpy(s1[None]).cuda()})
            with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
                probs[name].append(model(x).float().softmax(1)[0, 1].cpu().numpy())
    if len(models) > 1:
        probs["mean"] = [np.mean(ps, axis=0) for ps in zip(*[probs[n] for _, _, n in models])]
    for name, ps in probs.items():
        tp = fp = fn = 0
        for i, p in zip(test, ps):
            y = cache.label[i]
            v, w, pr = y != -1, y == 1, p >= 0.5
            tp += int((pr & w & v).sum()); fp += int((pr & ~w & v).sum()); fn += int((~pr & w & v).sum())
        print(f"{name:10s} {how:10s} IoU {tp / (tp + fp + fn):.3f}  precision {tp / (tp + fp):.3f}  recall {tp / (tp + fn):.3f}", flush=True)
        res.setdefault(name, {})[how] = round(tp / (tp + fp + fn), 3)


# Threshold for the production setting (20 m overview input, mean of the radar models), chosen on validation
if len(models) > 1:
    def mean_probs(ids):
        out = []
        for i in ids:
            s1 = degrade(cache.s1[i].astype(np.float32), "avg20")
            ps = []
            for model, norm, _ in models:
                x = norm({"S1GRD": torch.from_numpy(s1[None]).cuda()})
                with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
                    ps.append(model(x).float().softmax(1)[0, 1].cpu().numpy())
            out.append(np.mean(ps, axis=0))
        return out

    def score(ids, probs, thr):
        tp = fp = fn = 0
        for i, p in zip(ids, probs):
            y = cache.label[i]
            v, w, pr = y != -1, y == 1, p >= thr
            tp += int((pr & w & v).sum()); fp += int((pr & ~w & v).sum()); fn += int((~pr & w & v).sum())
        return tp / (tp + fp + fn), tp / (tp + fp), tp / (tp + fn)

    pv, pt = mean_probs(val), mean_probs(test)
    sweep = {round(t, 2): score(val, pv, t)[0] for t in np.arange(0.2, 0.71, 0.05)}
    best = max(sweep, key=sweep.get)
    print("val sweep (mean, avg20):", {k: round(v, 3) for k, v in sweep.items()})
    iou, prec, rec = score(test, pt, best)
    print(f"chosen threshold {best}: test IoU {iou:.3f} precision {prec:.3f} recall {rec:.3f}", flush=True)
    res.update(threshold=float(best), calibrated_test_iou=round(iou, 3), calibrated_precision=round(prec, 3),
               calibrated_recall=round(rec, 3))
if OUT:
    res["source"] = "scripts/test_resolution.py " + " ".join(os.path.basename(r.rstrip("/")) for r in sys.argv[2:])
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1)
