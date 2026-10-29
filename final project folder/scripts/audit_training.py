"""Independent checks of the benchmark runs and of the radar model behind the atlas (run on the lab server).

    env/bin/python code/scripts/audit_training.py code      ->  runs/_analysis/audit_training.json

1. Every job of server/jobs_main.txt has a results.json made with the arguments the job asked for.
2. Splits: no chip in two of train / val / test; under leave-India-out no India chip in train or val, and the
   test split is exactly the India chips.
3. Model selection: the stored best validation IoU is the maximum of the validation history, the losses are
   finite, and the selected epoch is reported.
4. Frozen runs train only the decoder (trainable parameters far below the total).
5. Test scores recomputed from the saved probabilities and the labels agree with results.json.
6. Seeds: spread of the test IoU across seeds of the same configuration.
7. External check: mean IoU over water and dry pixels (the metric of the Prithvi-EO-2.0 and TerraMind papers)
   on the official test split.
8. Atlas input: radar backscatter of the Mahanadi passes (after the gamma0 -> sigma0 conversion) against the
   Sen1Floods11 training radar, for pixels each source calls water and dry.
"""
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

CODE = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "code")
HOME = os.path.dirname(CODE)
sys.path.insert(0, CODE)
from floodfm.data import Cache, chip_event  # noqa: E402
from floodfm.metrics import evaluate  # noqa: E402

cache = Cache(f"{HOME}/data/cache")
out = {"jobs": {}, "problems": []}


def problem(msg):
    out["problems"].append(msg)
    print("PROBLEM", msg, flush=True)


# 1-6: every job
jobs = [l.split() for l in open(f"{CODE}/server/jobs_main.txt") if l.strip()]
labels = {}
for name, *args in jobs:
    want = {a[2:]: args[i + 1] for i, a in enumerate(args)
            if a.startswith("--") and i + 1 < len(args) and not args[i + 1].startswith("--")}
    p = f"{HOME}/runs/{name}/results.json"
    if not os.path.exists(p):
        problem(f"{name}: no results.json")
        continue
    r = json.load(open(p))
    a = r["args"]
    for k, v in want.items():
        if k in a and str(a[k]) != str(v):
            problem(f"{name}: argument {k} = {a[k]}, job asked for {v}")
    hist = r["history"]
    losses = [h["loss"] for h in hist]
    vals = [h["val_iou"] for h in hist]
    if not all(np.isfinite(losses)):
        problem(f"{name}: non-finite training loss")
    if abs(max(vals) - r["best_val_iou"]) > 1e-9:
        problem(f"{name}: best_val_iou {r['best_val_iou']} is not the history maximum {max(vals)}")
    proto = a["protocol"]
    ids = {s: cache.split(proto, s) for s in ("train", "val", "test")}
    if a.get("train_frac", 1.0) < 1:
        ids["train"] = None  # nested subset of the full training split
    tr, va, te = (set(ids["train"] or cache.split(proto, "train")), set(ids["val"]), set(ids["test"]))
    if tr & va or tr & te or va & te:
        problem(f"{name}: overlapping splits")
    if proto == "lio":
        if any(chip_event(c) == "India" for c in tr | va):
            problem(f"{name}: India chip in train/val under leave-India-out")
        if not all(chip_event(c) == "India" for c in te):
            problem(f"{name}: non-India chip in the leave-India-out test split")
    if list(r["test"]["chips"]) != list(ids["test"]):
        problem(f"{name}: test chips differ from the split definition")
    # recompute the test score from the stored probabilities
    key = (proto, "test")
    if key not in labels:
        labels[key] = np.stack([cache.label[cache.pos[c]] for c in ids["test"]])
    prob = np.load(f"{HOME}/runs/{name}/prob_test.npy")
    again = evaluate(prob, labels[key], [chip_event(c) for c in ids["test"]])["pooled"]["iou"]
    if abs(again - r["test"]["pooled"]["iou"]) > 1e-9:
        problem(f"{name}: recomputed test IoU {again:.6f} != stored {r['test']['pooled']['iou']:.6f}")
    tp, fp, fn, tn = r["test"]["counts"]
    out["jobs"][name] = dict(protocol=proto, model=a["model"], mode=a["mode"], seed=a["seed"],
                             modalities=a.get("modalities") or "default", train_frac=a.get("train_frac", 1.0),
                             n_train_chips=r.get("n_train_chips"), best_epoch=r.get("best_epoch"), epochs=a["epochs"],
                             best_val_iou=round(r["best_val_iou"], 4), test_iou=round(r["test"]["pooled"]["iou"], 4),
                             test_iou_recomputed=round(again, 4), test_miou=round((tp / (tp + fp + fn) + tn / (tn + fp + fn)) / 2, 4),
                             trainable_share=round(r["params_trainable"] / r["params_total"], 4),
                             final_loss=round(losses[-1], 4), first_loss=round(losses[0], 4))
    if a["mode"] == "frozen" and r["params_trainable"] / r["params_total"] > 0.5:
        problem(f"{name}: frozen run trains {r['params_trainable']} of {r['params_total']} parameters")

J = out["jobs"]
groups = defaultdict(list)
for k, j in J.items():
    groups[(j["protocol"], j["model"], j["mode"], j["modalities"], j["train_frac"])].append(j)
out["seed_spread"] = {"/".join(map(str, g)): dict(n=len(v), mean=round(float(np.mean([x["test_iou"] for x in v])), 4),
                                                   sd=round(float(np.std([x["test_iou"] for x in v])), 4),
                                                   best_epochs=[x["best_epoch"] for x in v])
                      for g, v in sorted(groups.items())}
out["split_sizes"] = {p: {s: len(cache.split(p, s)) for s in ("train", "val", "test", "bolivia")} for p in ("official", "lio")}
out["india_chips_in_official_train"] = sum(chip_event(c) == "India" for c in cache.split("official", "train"))
out["official_test_miou"] = {k: dict(water_iou=j["test_iou"], miou=j["test_miou"]) for k, j in J.items()
                             if j["protocol"] == "official" and j["mode"] == "full" and j["seed"] == 0 and j["train_frac"] == 1.0}
out["best_epoch_at_last_epoch"] = sorted(k for k, j in J.items() if j["best_epoch"] == j["epochs"])

# 8: atlas radar against the training radar
import rasterio  # noqa: E402

rng = np.random.default_rng(0)
tr_vv, tr_vh, tr_y = [], [], []
for c in rng.choice(cache.split("official", "train"), 60, replace=False):
    s1 = cache.s1[cache.pos[c]][:, ::4, ::4]
    y = cache.label[cache.pos[c]][::4, ::4]
    ok = (y >= 0) & (s1 > -80).all(0) & np.isfinite(s1).all(0)
    tr_vv.append(s1[0][ok]); tr_vh.append(s1[1][ok]); tr_y.append(y[ok])
tr_vv, tr_vh, tr_y = map(np.concatenate, (tr_vv, tr_vh, tr_y))
GAMMA_TO_SIGMA_DB = 10 * np.log10(np.cos(np.deg2rad(37.0)))
inv = __import__("pandas").read_csv(f"{HOME}/data/mahanadi_atlas20/inventory.csv")
scenes = sorted(glob.glob(f"{HOME}/data/mahanadi_atlas20/S1_2*_*.tif"))
mon = [s for s in scenes if os.path.basename(s)[7:9] in ("07", "08", "09", "10")]
at_vv, at_vh, at_w = [], [], []
for s in rng.choice(mon, 24, replace=False):
    base = os.path.basename(s)[:-4]
    with rasterio.open(s) as src:
        raw = src.read()[:, ::3, ::3].astype(np.float64)
    pt = f"{HOME}/runs/_atlas/prob/{base}_terramind.tif"
    pu = f"{HOME}/runs/_atlas/prob/{base}_unet.tif"
    if not (os.path.exists(pt) and os.path.exists(pu)):
        continue
    with rasterio.open(pt) as a_, rasterio.open(pu) as b_:
        pa, pb = a_.read(1)[::3, ::3], b_.read(1)[::3, ::3]
    ok = (raw > -32768).all(0) & (pa < 255) & (pb < 255)
    db = raw / 100.0 + GAMMA_TO_SIGMA_DB
    w = (pa.astype(float) + pb) / 2 / 254 >= 0.30
    at_vv.append(db[0][ok]); at_vh.append(db[1][ok]); at_w.append(w[ok])
at_vv, at_vh, at_w = map(np.concatenate, (at_vv, at_vh, at_w))


def q(v):
    return [round(float(x), 2) for x in np.percentile(v, [10, 50, 90])] if v.size else []


out["radar_db_percentiles_10_50_90"] = {
    "sen1floods11_train_water": {"VV": q(tr_vv[tr_y == 1]), "VH": q(tr_vh[tr_y == 1])},
    "sen1floods11_train_dry": {"VV": q(tr_vv[tr_y == 0]), "VH": q(tr_vh[tr_y == 0])},
    "mahanadi_atlas_water": {"VV": q(at_vv[at_w]), "VH": q(at_vh[at_w])},
    "mahanadi_atlas_dry": {"VV": q(at_vv[~at_w]), "VH": q(at_vh[~at_w])},
    "note": "Mahanadi: 24 random Jul-Oct passes, after the gamma0 -> sigma0 conversion used by atlas_infer.py; "
            "water = fused probability >= 0.30. Sen1Floods11: 60 random official-train chips, hand labels."}
out["n_jobs"] = len(jobs)
out["n_checked"] = len(J)
json.dump(out, open(f"{HOME}/runs/_analysis/audit_training.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ("jobs", "seed_spread")}, indent=1))
print("AUDIT_DONE", len(J), "runs,", len(out["problems"]), "problems")
