"""Collect every run, calibrate thresholds, build the fusion models, write tables and figures.

    python scripts/analyze.py <code_dir>      ->  runs/_analysis/{*.csv,*.json,figures/*.png}

Fusion ("fuse layer") follows the mentor's plan of combining the fine-tuned models. Member sets:
the six foundation models (ens_*), all eight trained models incl. CNN and U-Net (ensall_*), and the
three best by validation IoU (enstop3_*). Combination rules, all fitted on VALIDATION predictions
only and scored once on test:
  *_mean      equal-weight average of member water probabilities
  *_weighted  average weighted by each member's validation IoU
  *_learned   logistic-regression fuse layer on the members' logits (a learned 1x1 conv)
"""
import glob
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, sys.argv[1])
from floodfm.data import Cache, chip_event  # noqa: E402
from floodfm.metrics import evaluate, threshold_sweep  # noqa: E402

HOME = "/home1/vineet/floodfm"
OUT = f"{HOME}/runs/_analysis"
os.makedirs(f"{OUT}/figures", exist_ok=True)
cache = Cache(f"{HOME}/data/cache")
FMS = ["prithvi", "terramind", "dofa", "clay", "satlas", "decur"]
NAMES = {"otsu_vh": "Otsu (VH radar)", "ndwi": "NDWI > 0", "mndwi": "MNDWI > 0",
         "prithvi_published": "Prithvi published ckpt", "cnn": "Simple CNN", "unet": "U-Net",
         "prithvi": "Prithvi-EO-2.0-300M", "terramind": "TerraMind-B", "dofa": "DOFA-B", "clay": "Clay-v1-B",
         "satlas": "Satlas Swin-B", "decur": "DeCUR ResNet-50", "ens_mean": "Fusion 6 FMs: mean",
         "ens_weighted": "Fusion 6 FMs: val-weighted", "ens_learned": "Fusion 6 FMs: learned layer",
         "ensall_mean": "Fusion all 8: mean", "ensall_learned": "Fusion all 8: learned layer",
         "enstop3_mean": "Fusion top-3 (val): mean"}
ENS = ["ens_mean", "ens_weighted", "ens_learned", "ensall_mean", "ensall_learned", "enstop3_mean"]
GROUP = {"otsu_vh": "no training", "ndwi": "no training", "mndwi": "no training",
         "prithvi_published": "no training", "cnn": "from scratch", "unet": "from scratch",
         **{k: "fusion" for k in ["ens_mean", "ens_weighted", "ens_learned", "ensall_mean", "ensall_learned",
                                  "enstop3_mean"]}}
COLOR = {"no training": "#8a8984", "from scratch": "#2a78d6", "foundation model": "#eb6834", "fusion": "#1baf7a"}


def parse(name):
    m = re.match(r"(official|lio)_(.+?)(?:_(s1|s2))?_(full|frozen)_s(\d)$", name)
    if m:
        return dict(protocol=m[1], model=m[2], modalities=m[3] or "default", mode=m[4], seed=int(m[5]))
    m = re.match(r"(official|lio)_(otsu_vh|ndwi|mndwi|prithvi_published)$", name)
    if m:
        return dict(protocol=m[1], model=m[2], modalities="default", mode="none", seed=0)
    return None


runs = []
for f in sorted(glob.glob(f"{HOME}/runs/*/results.json")):
    name = os.path.basename(os.path.dirname(f))
    p = parse(name)
    if p is None:
        continue
    r = json.load(open(f))
    p.update(name=name, dir=os.path.dirname(f), res=r)
    runs.append(p)
print(len(runs), "runs found")

labels, events, jrcs = {}, {}, {}
for proto in ("official", "lio"):
    for split in ("val", "test", "bolivia"):
        ids = cache.split(proto, split)
        labels[proto, split] = np.stack([cache.label[cache.pos[c]] for c in ids])
        jrcs[proto, split] = np.stack([cache.jrc[cache.pos[c]] for c in ids])
        events[proto, split] = [chip_event(c) for c in ids]


def prob(run, split):
    return np.load(f"{run['dir']}/prob_{split}.npy")


# ---------- threshold calibration (choose on validation, apply to test) ----------
for r in runs:
    sweep = threshold_sweep(prob(r, "val"), labels[r["protocol"], "val"])
    best = max(sweep, key=lambda s: s["iou"])
    r["thr"] = best["threshold"]
    r["test_cal"] = evaluate(prob(r, "test"), labels[r["protocol"], "test"],
                             events[r["protocol"], "test"], thr=best["threshold"])["pooled"]
    r["sweep_test"] = threshold_sweep(prob(r, "test"), labels[r["protocol"], "test"])


# ---------- fusion ----------
def fuse(members, proto, seed, prefix):
    from sklearn.linear_model import LogisticRegression
    out = {}
    lv = labels[proto, "val"]
    pv = [prob(m, "val").astype(np.float32) / 255 for m in members]
    w = np.array([m["res"]["best_val_iou"] for m in members])
    rng = np.random.default_rng(seed)
    valid = lv >= 0
    idx = np.flatnonzero(valid.ravel())
    idx = rng.choice(idx, min(400_000, idx.size), replace=False)
    logit = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))  # noqa: E731
    X = np.stack([logit(p.ravel()[idx]) for p in pv], 1)
    y = (lv.ravel()[idx] == 1).astype(int)
    lr = LogisticRegression(max_iter=500).fit(X, y)
    out["coef"] = dict(zip([m["model"] for m in members], lr.coef_[0].round(3).tolist()))
    for split in ("val", "test", "bolivia"):
        ps = [prob(m, split).astype(np.float32) / 255 for m in members]
        mean = np.mean(ps, 0)
        wavg = np.tensordot(w / w.sum(), np.stack(ps), 1)
        Z = np.stack([logit(p) for p in ps], -1)
        learned = 1 / (1 + np.exp(-(Z @ lr.coef_[0] + lr.intercept_[0])))
        for k, v in (("mean", mean), ("weighted", wavg), ("learned", learned)):
            out.setdefault(f"{prefix}_{k}", {})[split] = (v * 255).round().astype(np.uint8)
    return out


ens_runs = []
for proto in ("official", "lio"):
    for seed in (0, 1, 2):
        trained = [r for r in runs if r["protocol"] == proto and r["mode"] == "full" and r["seed"] == seed
                   and r["modalities"] == "default" and r["model"] in FMS + ["cnn", "unet"]]
        fms = [r for r in trained if r["model"] in FMS]
        if len(fms) < 6 or len(trained) < 8:
            continue
        top3 = sorted(trained, key=lambda r: -r["res"]["best_val_iou"])[:3]
        f = {}
        for prefix, members, keep in (("ens", fms, ("mean", "weighted", "learned")),
                                      ("ensall", trained, ("mean", "learned")), ("enstop3", top3, ("mean",))):
            fr = fuse(members, proto, seed, prefix)
            for kk in keep:
                f[f"{prefix}_{kk}"] = fr[f"{prefix}_{kk}"]
                f[f"{prefix}_{kk}_members"] = {"members": [m["model"] for m in members], "coef": fr["coef"]}
        for k in ENS:
            res = dict(f[f"{k}_members"])
            for split in ("val", "test", "bolivia"):
                res[split] = evaluate(f[k][split], labels[proto, split], events[proto, split],
                                      jrc=jrcs[proto, split])
            d = f"{HOME}/runs/{proto}_{k}_s{seed}"
            os.makedirs(d, exist_ok=True)
            for split in ("val", "test", "bolivia"):
                np.save(f"{d}/prob_{split}.npy", f[k][split])
            json.dump(res, open(f"{d}/results.json", "w"))
            er = dict(protocol=proto, model=k, modalities="default", mode="full", seed=seed, name=f"{proto}_{k}_s{seed}",
                      dir=d, res=res)
            sweep = threshold_sweep(f[k]["val"], labels[proto, "val"])
            er["thr"] = max(sweep, key=lambda s: s["iou"])["threshold"]
            er["test_cal"] = evaluate(f[k]["test"], labels[proto, "test"], events[proto, "test"], thr=er["thr"])["pooled"]
            ens_runs.append(er)
runs += ens_runs


# ---------- summary table: mean +- std over seeds ----------
def agg(rows, key):
    v = np.array([key(r) for r in rows], float)
    return float(v.mean()), float(v.std(ddof=1)) if len(v) > 1 else 0.0, len(v)


summary = []
groups = {}
for r in runs:
    groups.setdefault((r["protocol"], r["model"], r["mode"], r["modalities"]), []).append(r)
for (proto, model, mode, mods), rows in sorted(groups.items()):
    row = dict(protocol=proto, model=model, label=NAMES.get(model, model), mode=mode, modalities=mods,
               group=GROUP.get(model, "foundation model"), n_seeds=len(rows))
    for nm, fn in [("test_iou", lambda r: r["res"]["test"]["pooled"]["iou"]),
                   ("test_f1", lambda r: r["res"]["test"]["pooled"]["f1"]),
                   ("test_precision", lambda r: r["res"]["test"]["pooled"]["precision"]),
                   ("test_recall", lambda r: r["res"]["test"]["pooled"]["recall"]),
                   ("test_iou_calibrated", lambda r: r["test_cal"]["iou"]),
                   ("threshold", lambda r: r["thr"]),
                   ("test_mean_chip_iou", lambda r: r["res"]["test"]["mean_chip_iou"]),
                   ("test_nonpermanent_iou", lambda r: r["res"]["test"]["non_permanent"]["iou"]),
                   ("bolivia_iou", lambda r: r["res"]["bolivia"]["pooled"]["iou"]),
                   ("val_iou", lambda r: r["res"]["val"]["pooled"]["iou"])]:
        m, s, _ = agg(rows, fn)
        row[nm] = round(m, 4)
        row[nm + "_std"] = round(s, 4)
    r0 = rows[0]["res"]
    row["params_M"] = round(r0.get("params_total", 0) / 1e6, 1)
    row["trainable_M"] = round(r0.get("params_trainable", 0) / 1e6, 1)
    row["train_min"] = round(np.mean([r["res"].get("train_time_s", 0) for r in rows]) / 60, 1)
    row["ms_per_chip"] = round(1000 * np.mean([r["res"].get("infer_s_per_chip_test", 0) for r in rows]), 1)
    row["best_epoch"] = round(float(np.mean([r["res"].get("best_epoch", 0) for r in rows])), 1)
    summary.append(row)

import csv  # noqa: E402
with open(f"{OUT}/summary.csv", "w", newline="") as fh:
    wr = csv.DictWriter(fh, fieldnames=list(summary[0].keys()))
    wr.writeheader()
    wr.writerows(summary)
json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=1)

# per-event table (official protocol, seed-averaged, full fine-tune + baselines)
pe = {}
for r in runs:
    if r["protocol"] != "official" or r["modalities"] != "default" or r["mode"] == "frozen":
        continue
    for e, s in r["res"]["test"]["per_event"].items():
        pe.setdefault(r["model"], {}).setdefault(e, []).append(s["iou"])
pe = {m: {e: round(float(np.mean(v)), 4) for e, v in d.items()} for m, d in pe.items()}
json.dump(pe, open(f"{OUT}/per_event_official.json", "w"), indent=1)
json.dump({r["name"]: {"thr": r["thr"], "coef": r["res"].get("coef")} for r in runs},
          open(f"{OUT}/thresholds.json", "w"), indent=1)
json.dump({r["name"]: r.get("sweep_test") for r in runs if r.get("sweep_test")},
          open(f"{OUT}/sweeps_test.json", "w"))
json.dump({r["name"]: r["res"].get("history") for r in runs if r["res"].get("history")},
          open(f"{OUT}/histories.json", "w"))

# ---------- figures ----------
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#8a8984", "axes.labelcolor": "#52514e", "xtick.color": "#52514e",
                     "ytick.color": "#52514e", "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6,
                     "axes.axisbelow": True})
ORDER = ["otsu_vh", "mndwi", "ndwi", "prithvi_published", "cnn", "unet"] + FMS + ENS


def bar_figure(proto, metric, title, fname):
    rows = [s for s in summary if s["protocol"] == proto and s["modalities"] == "default" and s["mode"] in ("full", "none")
            and s["model"] in ORDER]
    rows = sorted(rows, key=lambda s: ORDER.index(s["model"]))
    fig, ax = plt.subplots(figsize=(7.2, 0.32 * len(rows) + 1.0))
    y = np.arange(len(rows))[::-1]
    for yi, s in zip(y, rows):
        ax.barh(yi, s[metric], xerr=s[metric + "_std"] if s["n_seeds"] > 1 else None, height=0.6,
                color=COLOR[s["group"]], error_kw=dict(ecolor="#52514e", lw=1, capsize=2))
        ax.text(s[metric] + 0.01 + s[metric + "_std"], yi, f"{s[metric]:.3f}", va="center", fontsize=8, color="#0b0b0b")
    ax.set_yticks(y)
    ax.set_yticklabels([s["label"] for s in rows])
    ax.set_xlim(0, 1)
    ax.set_xlabel("Water IoU on test (mean ± sd over seeds)")
    ax.set_title(title, loc="left", fontsize=10)
    ax.grid(axis="y", visible=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in COLOR.values()]
    ax.legend(handles, list(COLOR.keys()), loc="upper right", frameon=True, framealpha=0.9, edgecolor="none", fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{OUT}/figures/{fname}", dpi=160)
    plt.close(fig)


bar_figure("official", "test_iou", "Official Sen1Floods11 split (test, 90 chips)", "bars_official.png")
bar_figure("lio", "test_iou", "Unseen Indian flood: leave-India-out (Assam 2016, 68 chips)", "bars_lio.png")

# frozen vs fine-tuned (paired)
fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.0), sharey=True)
for ax, proto, ttl in zip(axes, ("official", "lio"), ("Official split", "Leave-India-out")):
    for k, m in enumerate(FMS):
        fz = next((s for s in summary if s["protocol"] == proto and s["model"] == m and s["mode"] == "frozen"), None)
        fu = next((s for s in summary if s["protocol"] == proto and s["model"] == m and s["mode"] == "full"
                   and s["modalities"] == "default"), None)
        if fz and fu:
            ax.plot([k, k], [fz["test_iou"], fu["test_iou"]], color="#c3c2b7", lw=2, zorder=1)
            ax.scatter(k, fz["test_iou"], s=36, color="#8a8984", zorder=2, label="frozen encoder" if k == 0 else None)
            ax.scatter(k, fu["test_iou"], s=36, color="#eb6834", zorder=2, label="fine-tuned" if k == 0 else None)
    ax.set_xticks(range(len(FMS)))
    ax.set_xticklabels([NAMES[m].split(" ")[0].split("-")[0] for m in FMS], rotation=30)
    ax.set_title(ttl, loc="left", fontsize=10)
axes[0].set_ylabel("Water IoU on test")
axes[0].legend(frameon=False, fontsize=8, loc="lower left")
fig.tight_layout()
fig.savefig(f"{OUT}/figures/frozen_vs_finetuned.png", dpi=160)
plt.close(fig)

# modality ablation on the unseen Indian event
abl = [(m, mods) for m in ("unet", "terramind") for mods in ("s1", "s2", "default")]
fig, ax = plt.subplots(figsize=(6.4, 2.8))
cols = {"s1": "#2a78d6", "s2": "#eda100", "default": "#1baf7a"}
labs = {"s1": "radar only (S1)", "s2": "optical only (S2)", "default": "radar + optical"}
for gi, m in enumerate(("unet", "terramind")):
    for k, mods in enumerate(("s1", "s2", "default")):
        s = next((s for s in summary if s["protocol"] == "lio" and s["model"] == m and s["mode"] == "full"
                  and s["modalities"] == mods), None)
        if s:
            x = gi * 4 + k
            ax.bar(x, s["test_iou"], yerr=s["test_iou_std"] if s["n_seeds"] > 1 else None, color=cols[mods],
                   width=0.8, label=labs[mods] if gi == 0 else None, error_kw=dict(ecolor="#52514e", capsize=2))
            ax.text(x, s["test_iou"] + 0.03, f"{s['test_iou']:.2f}", ha="center", fontsize=8)
ax.set_xticks([1, 5])
ax.set_xticklabels(["U-Net (from scratch)", "TerraMind-B (fine-tuned)"])
ax.set_ylim(0, 1)
ax.set_ylabel("Water IoU, Assam 2016")
ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
ax.grid(axis="x", visible=False)
fig.tight_layout()
fig.savefig(f"{OUT}/figures/modality_ablation.png", dpi=160)
plt.close(fig)

# threshold sweep (seed 0, lio) for a few models
fig, ax = plt.subplots(figsize=(6.0, 3.0))
pal = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"]
for c, m in zip(pal, ["unet", "prithvi", "terramind", "ens_mean"]):
    nm = f"lio_{m}_full_s0" if not m.startswith("ens") else f"lio_{m}_s0"
    r = next((r for r in runs if r["name"] == nm), None)
    if r and r.get("sweep_test"):
        t = [s["threshold"] for s in r["sweep_test"]]
        ax.plot(t, [s["iou"] for s in r["sweep_test"]], color=c, lw=2, label=NAMES[m])
        ax.axvline(r["thr"], color=c, lw=1, ls=":")
ax.set_xlabel("Decision threshold on water probability")
ax.set_ylabel("Water IoU, Assam 2016")
ax.legend(frameon=False, fontsize=8)
ax.set_title("Dotted lines: threshold chosen on validation (non-Indian events)", loc="left", fontsize=9)
fig.tight_layout()
fig.savefig(f"{OUT}/figures/threshold_sweep_lio.png", dpi=160)
plt.close(fig)

# precision-recall operating points (lio, seed-averaged)
fig, ax = plt.subplots(figsize=(4.6, 4.2))
for f1 in (0.5, 0.6, 0.7, 0.8, 0.9):
    r_ = np.linspace(f1 / (2 - f1) + 1e-3, 1, 100)
    ax.plot(r_, f1 * r_ / (2 * r_ - f1), color="#e6e5e0", lw=1)
    ax.text(1.0, f1 / (2 - f1), f"F1={f1}", fontsize=7, color="#8a8984", ha="right", va="bottom")
for s in summary:
    if s["protocol"] == "lio" and s["modalities"] == "default" and s["mode"] in ("full", "none") and s["model"] in ORDER:
        ax.scatter(s["test_recall"], s["test_precision"], s=30, color=COLOR[s["group"]], zorder=3)
        ax.annotate(s["label"].split(" ")[0].replace(":", ""), (s["test_recall"], s["test_precision"]), fontsize=6.5,
                    xytext=(3, 2), textcoords="offset points", color="#52514e")
ax.set_xlim(0.3, 1.0)
ax.set_ylim(0.2, 1.0)
ax.set_xlabel("Recall (share of true water found)")
ax.set_ylabel("Precision (share of predictions correct)")
ax.set_title("Assam 2016 operating points", loc="left", fontsize=10)
fig.tight_layout()
fig.savefig(f"{OUT}/figures/pr_points_lio.png", dpi=160)
plt.close(fig)

# label efficiency: nested subsets of the LIO training chips, same number of optimiser updates
le = {}
for s in summary:
    mm = re.match(r"(unet|terramind|prithvi)_frac(\d+)$", s["model"])
    if s["protocol"] == "lio" and mm:
        le.setdefault(mm[1], {})[int(mm[2])] = (s["test_iou"], s["test_iou_std"], s["n_seeds"])
for m in ("unet", "terramind", "prithvi"):
    full = next((s for s in summary if s["protocol"] == "lio" and s["model"] == m and s["mode"] == "full"
                 and s["modalities"] == "default"), None)
    if full and m in le:
        le[m][100] = (full["test_iou"], full["test_iou_std"], full["n_seeds"])
json.dump(le, open(f"{OUT}/label_efficiency.json", "w"), indent=1)
if le:
    n_train = len(cache.split("lio", "train"))
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    for c, m in zip(["#2a78d6", "#1baf7a", "#eb6834"], ["unet", "terramind", "prithvi"]):
        if m not in le:
            continue
        fr = sorted(le[m])
        x = [round(f / 100 * n_train) for f in fr]
        y = [le[m][f][0] for f in fr]
        e = [le[m][f][1] for f in fr]
        ax.errorbar(x, y, yerr=e, color=c, lw=2, marker="o", ms=5, capsize=3, label=NAMES[m])
    ax.set_xscale("log")
    ax.set_xticks([21, 53, 106, 212]); ax.set_xticklabels(["21 (10%)", "53 (25%)", "106 (50%)", "212 (100%)"])
    ax.set_xlabel("Labelled training chips (non-Indian events), same number of updates")
    ax.set_ylabel("Water IoU, Assam 2016")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{OUT}/figures/label_efficiency_lio.png", dpi=160)
    plt.close(fig)

# training curves (lio seed 0)
fig, ax = plt.subplots(figsize=(6.4, 3.0))
pal8 = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
for c, m in zip(pal8, ["cnn", "unet"] + FMS):
    r = next((r for r in runs if r["name"] == f"lio_{m}_full_s0"), None)
    if r:
        h = r["res"]["history"]
        ax.plot([e["epoch"] for e in h], [e["val_iou"] for e in h], color=c, lw=1.5, label=NAMES[m])
ax.set_xlabel("Epoch")
ax.set_ylabel("Validation IoU (non-Indian events)")
ax.legend(frameon=False, fontsize=7, ncol=2)
fig.tight_layout()
fig.savefig(f"{OUT}/figures/training_curves_lio.png", dpi=160)
plt.close(fig)


# error maps on Indian chips: RGB, VH, truth, U-Net errors, best-FM errors, fusion errors
def rgb(i):
    x = cache.s2[i][[3, 2, 1]].astype(np.float32).transpose(1, 2, 0)
    lo, hi = np.percentile(x, [2, 98])
    return np.clip((x - lo) / max(hi - lo, 1), 0, 1)


def err_map(lab, pred):
    e = np.full(lab.shape + (3,), 1.0)
    e[(lab == 0) & ~pred] = (0.94, 0.93, 0.90)
    e[(lab == 1) & pred] = (0.11, 0.21, 0.34)
    e[(lab == 0) & pred] = (0.89, 0.29, 0.28)
    e[(lab == 1) & ~pred] = (0.16, 0.47, 0.84)
    return e


lio_ids = cache.split("lio", "test")
lab_test = labels["lio", "test"]
frac = [((l == 1).sum() / max((l >= 0).sum(), 1)) for l in lab_test]
pick = [int(i) for i in np.argsort(np.abs(np.array(frac) - 0.3))[:4]]
best_fm = max([s for s in summary if s["protocol"] == "lio" and s["model"] in FMS and s["mode"] == "full"
               and s["modalities"] == "default"], key=lambda s: s["test_iou"], default=None)
cols_ = [("unet", "U-Net"), (best_fm["model"] if best_fm else "terramind", NAMES[best_fm["model"]] if best_fm else ""),
         ("enstop3_mean", "Fusion top-3")]
fig, axes = plt.subplots(len(pick), 6, figsize=(13, 2.3 * len(pick)))
for row, k in enumerate(pick):
    i = cache.pos[lio_ids[k]]
    vh = cache.s1[i][1].astype(np.float32)
    panels = [rgb(i), np.clip(np.nan_to_num(vh, nan=-30), -30, -5), np.where(lab_test[k] >= 0, lab_test[k], np.nan)]
    for m, _ in cols_:
        nm = f"lio_{m}_full_s0" if not m.startswith("ens") else f"lio_{m}_s0"
        r = next((r for r in runs if r["name"] == nm), None)
        panels.append(err_map(lab_test[k], prob(r, "test")[k] >= 128) if r else np.ones((512, 512, 3)))
    for c, pnl in enumerate(panels):
        axes[row, c].imshow(pnl, cmap="gray" if c == 1 else ("Blues" if c == 2 else None))
        axes[row, c].set_xticks([]); axes[row, c].set_yticks([])
        axes[row, c].grid(False)
    axes[row, 0].set_ylabel(lio_ids[k], fontsize=7)
for c, t in enumerate(["Sentinel-2 RGB", "Sentinel-1 VH", "Hand label"] + [f"{n} errors" for _, n in cols_]):
    axes[0, c].set_title(t, fontsize=9)
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in [(0.94, 0.93, 0.90), (0.11, 0.21, 0.34), (0.89, 0.29, 0.28), (0.16, 0.47, 0.84)]]
fig.legend(handles, ["correct dry", "correct water", "false alarm", "missed water"], loc="lower center", ncol=4,
           frameon=False, fontsize=9)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(f"{OUT}/figures/error_maps_assam.png", dpi=130)
plt.close(fig)

print("analysis written to", OUT)
for s in summary:
    print(f"{s['protocol']:8s} {s['label']:26s} {s['mode']:6s} {s['modalities']:7s} n={s['n_seeds']} "
          f"IoU {s['test_iou']:.3f}±{s['test_iou_std']:.3f} cal {s['test_iou_calibrated']:.3f}@{s['threshold']:.2f} "
          f"P {s['test_precision']:.3f} R {s['test_recall']:.3f} nonperm {s['test_nonpermanent_iou']:.3f} "
          f"bol {s['bolivia_iou']:.3f}")
