"""A learned flow + rain + history model of flooded land, tested exactly like the trigger map (leave-one-year-out).

    ATLAS_DIR=runs/_atlas/build_r20 python mahanadi/learned_flood_model.py --context data/mahanadi_context \
        --out runs/_atlas/learned_r20

The trigger map uses the Naraj flow alone; the analog maps use flow and rain only through similar past passes. Here a
gradient-boosted classifier (scikit-learn HistGradientBoosting) sees, for every pixel of every monsoon pass, the
flow and 7-day rain of the pass, its month and radar track, and what the training years say about the pixel: its
trigger discharge, its flood frequency overall, at high flows and in heavy rain, its height above the nearest river
bed and its distance to it, with the physical direction of each input imposed (monotonic constraints). Each year is
predicted by a model fitted on the other years only, and a pixel is called
flooded when its probability is >= 0.5, the same per-pixel error-minimising rule as the trigger fit, so the scores
compare like with like. Trigger map and climatology are scored again here on the same passes and pixels.
Outputs: learned_summary.json, learned_passes.csv, learned_scenarios.tif (design floods with typical and heavy rain).
"""
import argparse
import json
import os
import time

import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score

ap = argparse.ArgumentParser()
ap.add_argument("--context", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--per-pass", type=int, default=3000, help="training pixels sampled per pass")
a = ap.parse_args()
ATLAS = os.environ["ATLAS_DIR"]
os.makedirs(a.out, exist_ok=True)
t0 = time.time()
PIX_KM2 = 400 / 1e6
S = json.load(open(f"{ATLAS}/atlas_summary.json"))
Q90 = S["validation"]["high_flow_passes"]["q90_threshold_m3s"] - 0.5   # stored rounded to 1 m3/s
R90 = S["validation"]["high_rain_passes"]["r90_threshold_mm"] - 0.05  # stored rounded to 0.1 mm
lib = np.load(f"{ATLAS}/flood_library.npz", allow_pickle=True)
H, W = (int(v) for v in lib["shape"])
N = H * W
names = [str(s) for s in lib["names"]]
q, r = lib["q"].astype(float), lib["r"].astype(float)
year = np.array([int(s[3:7]) for s in names])
month = np.array([int(s[7:9]) for s in names])
TRACKS = {"D048": 0, "D121": 1, "A085": 2}
track = np.array([TRACKS.get(s[-4:], 3) for s in names])
YEARS = sorted(set(year))
FLp, VLp = lib["fl"], lib["vl"]


def row(packed, i):
    return np.unpackbits(packed[i])[:N].astype(bool)


# per-year counts on the full grid: all passes, high-flow passes, heavy-rain passes
cnt = {k: {y: np.zeros(N, np.int16) for y in YEARS} for k in ("f", "v", "fh", "vh", "fr", "vr")}
for i in range(len(names)):
    f, v, y = row(FLp, i), row(VLp, i), year[i]
    cnt["f"][y] += f
    cnt["v"][y] += v
    if q[i] >= Q90:
        cnt["fh"][y] += f
        cnt["vh"][y] += v
    if r[i] >= R90:
        cnt["fr"][y] += f
        cnt["vr"][y] += v
tot = {k: sum(d.values()).astype(np.int32) for k, d in cnt.items()}
cand = np.flatnonzero((tot["f"] > 0) & (tot["v"] >= 10))  # pixels that ever flooded (the fold rule narrows this)
print(f"{len(names)} passes, {len(cand):,} candidate pixels, {time.time() - t0:.0f} s", flush=True)
FLc = np.zeros((len(names), len(cand)), bool)
VLc = np.zeros((len(names), len(cand)), bool)
for i in range(len(names)):
    FLc[i], VLc[i] = row(FLp, i)[cand], row(VLp, i)[cand]

# static pixel features: elevation, height above the nearest river-bed pixel, distance to the river bed
with rasterio.open(f"{a.context}/grid20_dem.tif") as src:
    dem = src.read(1).astype(np.float32)
    prof = src.profile
with rasterio.open(f"{ATLAS}/river_bed.tif") as src:
    bed = src.read(1).astype(bool)
dist, (ii, jj) = ndimage.distance_transform_edt(~bed, return_indices=True)
hand = (dem - dem[ii, jj]).ravel()[cand]
dist = (dist * 20.0).ravel()[cand].astype(np.float32)
demc = dem.ravel()[cand]
with rasterio.open(f"{ATLAS}/trigger_discharge_loyo.tif") as src:
    theta_fold = {y: src.read(k + 1).ravel() for k, y in enumerate(YEARS)}
with rasterio.open(f"{ATLAS}/trigger_discharge.tif") as src:
    theta_all = src.read(1).ravel()


def tlog(th):
    """Trigger discharge as log10 m3/s; never flooded -> 7, always wet -> 0, too few observations -> NaN."""
    return np.where(np.isfinite(th), np.log10(np.clip(th, 1.0, 1e7)), np.nan).astype(np.float32)


def pixel_features(theta, f, v, fh, vh, fr, vr):
    def frac(a_, b_, nmin):
        return np.where(b_ >= nmin, a_ / np.maximum(b_, 1), np.nan).astype(np.float32)
    return np.column_stack([tlog(theta[cand]), frac(f[cand], v[cand], 10), frac(fh[cand], vh[cand], 3),
                            frac(fr[cand], vr[cand], 3), demc, hand, dist])


PIX_NAMES = ["trigger_log10_q", "freq_all", "freq_high_flow", "freq_heavy_rain", "elevation_m", "height_above_bed_m",
             "distance_to_bed_m"]
PASS_NAMES = ["flow_q_max_5d", "rain_7d_mm", "month", "track", "flow_minus_trigger_log10"]
FEATURES = PASS_NAMES + PIX_NAMES


def design(i_or_vals, px):
    qi, ri, mi, ti = i_or_vals
    n_ = len(px)
    return np.column_stack([np.full(n_, qi, np.float32), np.full(n_, ri, np.float32), np.full(n_, mi, np.float32),
                            np.full(n_, ti, np.float32), (np.log10(max(qi, 1.0)) - px[:, 0]).astype(np.float32), px])


# Physical direction of each input: more flow, more rain, a flow further above the trigger or a pixel that flooded more
# often never lowers the flood probability; a higher trigger or more height above the river bed never raises it. Without
# these constraints a first run gave less flooded land for heavy rain than for typical rain at the 25-year flow.
MONOTONE = {"flow_q_max_5d": 1, "rain_7d_mm": 1, "flow_minus_trigger_log10": 1, "trigger_log10_q": -1, "freq_all": 1,
            "freq_high_flow": 1, "freq_heavy_rain": 1, "height_above_bed_m": -1}


def model():
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.1, max_leaf_nodes=63, min_samples_leaf=200,
                                          l2_regularization=1.0, early_stopping=True, validation_fraction=0.1,
                                          categorical_features=[FEATURES.index("track")],
                                          monotonic_cst=[MONOTONE.get(f, 0) for f in FEATURES], random_state=0)


# settlements, same rule as atlas_build.py / impact_exposure.py
with rasterio.open(f"{a.context}/grid20_pop.tif") as src:
    popg = np.nan_to_num(src.read(1).astype(np.float64))
slab, nsl = ndimage.label(ndimage.binary_dilation(popg / PIX_KM2 >= 1000, iterations=1), structure=np.ones((3, 3)))
sid = np.arange(1, nsl + 1)
sid = sid[ndimage.sum(popg, slab, sid) >= 200]
spop = ndimage.sum(popg, slab, sid)


def flagged(mask, valid):
    vp = ndimage.sum(popg * valid, slab, sid)
    share = ndimage.sum(popg * (mask & valid), slab, sid) / np.maximum(vp, 1)
    return share >= 0.10, vp >= 0.8 * spop


rng = np.random.default_rng(0)
METHODS = ("learned", "trigger", "climatology")
rows, auc_y, auc_s, auc_hf, auc_hr = [], [], {m: [] for m in METHODS}, [], []
sett = {m: np.zeros((3, 3), int) for m in METHODS}
importances = []
for y in YEARS:
    test = np.flatnonzero(year == y)
    train = np.flatnonzero(year != y)
    tr = {k: (tot[k] - cnt[k][y]) for k in cnt}
    px = pixel_features(theta_fold[y], tr["f"], tr["v"], tr["fh"], tr["vh"], tr["fr"], tr["vr"])
    fold_cand = (tr["f"][cand] > 0) & (tr["v"][cand] >= 10)
    Xs, ys = [], []
    for i in train:
        ok = np.flatnonzero(VLc[i] & fold_cand)
        if len(ok) == 0:
            continue
        pick = rng.choice(ok, size=min(len(ok), a.per_pass), replace=False)
        Xs.append(design((q[i], r[i], month[i], track[i]), px[pick]))
        ys.append(FLc[i, pick])
    clf = model().fit(np.concatenate(Xs), np.concatenate(ys))
    th_full = theta_fold[y]
    clim = (tr["v"] >= 10) & (tr["f"] >= 0.5 * tr["v"])
    fr_train = np.where(tr["v"] >= 10, tr["f"] / np.maximum(tr["v"], 1), 0.0)
    held_X, held_y = [], []
    for i in test:
        Fi, Vi = row(FLp, i), row(VLp, i)
        p = np.zeros(N, np.float32)
        p[cand[fold_cand]] = clf.predict_proba(design((q[i], r[i], month[i], track[i]), px[fold_cand]))[:, 1]
        preds = {"learned": p >= 0.5, "trigger": np.isfinite(th_full) & (th_full <= q[i]), "climatology": clim}
        rec = dict(name=names[i], year=int(y), q=q[i], r=r[i], high_flow=bool(q[i] >= Q90), high_rain=bool(r[i] >= R90),
                   obs_km2=float(Fi.sum() * PIX_KM2))
        for m, pm in preds.items():
            rec[f"{m}_tp"] = int((pm & Fi & Vi).sum())
            rec[f"{m}_fp"] = int((pm & ~Fi & Vi).sum())
            rec[f"{m}_fn"] = int((~pm & Fi & Vi).sum())
            rec[f"{m}_km2"] = float((pm & Vi).sum() * PIX_KM2)
        rows.append(rec)
        obs_f, ok_s = flagged(Fi.reshape(H, W), Vi.reshape(H, W))
        for m, pm in preds.items():
            pf, _ = flagged(pm.reshape(H, W), Vi.reshape(H, W))
            c3 = np.array([(pf & obs_f & ok_s).sum(), (~pf & obs_f & ok_s).sum(), (pf & ~obs_f & ok_s).sum()])
            sett[m][0] += c3
            if q[i] >= Q90:
                sett[m][1] += c3
            if r[i] >= R90:
                sett[m][2] += c3
        vp = np.flatnonzero(Vi)
        if len(vp):
            s_ = rng.choice(vp, size=min(len(vp), 40000), replace=False)
            auc_y.append(Fi[s_])
            auc_s["learned"].append(p[s_])
            auc_s["trigger"].append(np.where(np.isfinite(th_full[s_]), -th_full[s_].astype(np.float64), -2e7))
            auc_s["climatology"].append(fr_train[s_])
            auc_hf.append(np.full(len(s_), q[i] >= Q90))
            auc_hr.append(np.full(len(s_), r[i] >= R90))
        ok = np.flatnonzero(VLc[i] & fold_cand)
        if len(ok):
            pick = rng.choice(ok, size=min(len(ok), 600), replace=False)
            held_X.append(design((q[i], r[i], month[i], track[i]), px[pick]))
            held_y.append(FLc[i, pick])
    hx, hy = np.concatenate(held_X), np.concatenate(held_y)
    if hy.any() and (~hy).any():
        pi = permutation_importance(clf, hx, hy, scoring="roc_auc", n_repeats=3, random_state=0, n_jobs=1)
        importances.append(pi.importances_mean)
    print(f"LOYO {y}: {len(test)} passes, {len(np.concatenate(ys)):,} training pixels, "
          f"{clf.n_iter_} trees, {time.time() - t0:.0f} s", flush=True)

df = pd.DataFrame(rows)
df.to_csv(f"{a.out}/learned_passes.csv", index=False)


def iou(d, m):
    tp, fp, fn = d[f"{m}_tp"].sum(), d[f"{m}_fp"].sum(), d[f"{m}_fn"].sum()
    return dict(iou=round(tp / max(tp + fp + fn, 1), 3), precision=round(tp / max(tp + fp, 1), 3),
                recall=round(tp / max(tp + fn, 1), 3))


def skill(c3):
    h, m_, f = (int(v) for v in c3)
    return dict(hits=h, misses=m_, false_alarms=f, POD=round(h / max(h + m_, 1), 3), FAR=round(f / max(h + f, 1), 3),
                CSI=round(h / max(h + m_ + f, 1), 3))


yy = np.concatenate(auc_y)
subsets = {"all_passes": np.ones(len(yy), bool), "high_flow_passes": np.concatenate(auc_hf),
           "heavy_rain_passes": np.concatenate(auc_hr)}
out = {"method": "HistGradientBoosting per pixel and pass, leave-one-year-out, flooded if p >= 0.5",
       "features": FEATURES, "n_passes": int(len(df)), "candidate_pixels": int(len(cand)),
       "pixel_iou": {sub: {m: iou(d, m) for m in METHODS} | {"n": int(len(d))}
                     for sub, d in (("all_passes", df), ("high_flow_passes", df[df.high_flow]),
                                    ("heavy_rain_passes", df[df.high_rain]))},
       "per_year_iou": {int(y_): {m: iou(g, m)["iou"] for m in METHODS} for y_, g in df.groupby("year")},
       "area_correlation": {m: round(float(df[["obs_km2", f"{m}_km2"]].corr().iloc[0, 1]), 3) for m in ("learned", "trigger")},
       "settlements": {sub: {m: skill(sett[m][j]) for m in METHODS}
                       for j, sub in enumerate(("all_passes", "high_flow_passes", "heavy_rain_passes"))},
       "ranking_auc": {sub: {m: round(float(roc_auc_score(yy[sel], np.concatenate(auc_s[m])[sel])), 3) for m in METHODS}
                       for sub, sel in subsets.items() if yy[sel].any() and (~yy[sel]).any()},
       "permutation_importance_auc_drop": dict(sorted({f: round(float(v), 4) for f, v in
                                                       zip(FEATURES, np.mean(importances, axis=0))}.items(),
                                                      key=lambda kv: -kv[1])) if importances else {}}

# final model on all years, then design floods with typical and with heavy rain
px = pixel_features(theta_all, tot["f"], tot["v"], tot["fh"], tot["vh"], tot["fr"], tot["vr"])
Xs, ys = [], []
for i in range(len(names)):
    ok = np.flatnonzero(VLc[i])
    pick = rng.choice(ok, size=min(len(ok), a.per_pass), replace=False)
    Xs.append(design((q[i], r[i], month[i], track[i]), px[pick]))
    ys.append(FLc[i, pick])
final = model().fit(np.concatenate(Xs), np.concatenate(ys))
RP = {int(k): v for k, v in S["gumbel"]["return_period_m3s"].items()}
r_typ = float(np.median(r))
r_heavy = float(S.get("heavy_rain_scenario", {}).get("rain_mm", np.percentile(r, 95)))
with rasterio.open(f"{ATLAS}/normal_water_latest.tif") as src:
    land = ~src.read(1).astype(bool).ravel()
scen, bands, names_b = {}, [], []
for label, qv, rv in ([(f"T{T} typical rain", RP[T], r_typ) for T in (2, 5, 25)] +
                      [(f"T{T} heavy rain", RP[T], r_heavy) for T in (2, 5, 25)] + [("T5 dry week", RP[5], 20.0)]):
    p = np.zeros(N, np.float32)
    p[cand] = np.mean([final.predict_proba(design((qv, rv, 8, t), px))[:, 1] for t in (0, 1, 2)], axis=0)
    m = (p >= 0.5) & land
    scen[label] = dict(flow_m3s=round(qv), rain_7d_mm=round(rv), flood_km2=round(float(m.sum() * PIX_KM2), 1),
                       people=round(float((popg.ravel() * m).sum())))
    bands.append(m.reshape(H, W).astype(np.uint8))
    names_b.append(label)
prof.update(count=len(bands), dtype="uint8", nodata=None, compress="deflate")
with rasterio.open(f"{a.out}/learned_scenarios.tif", "w", **prof) as dst:
    dst.write(np.stack(bands))
    dst.update_tags(bands=";".join(names_b))
out["scenarios_all_years_model"] = scen
out["scenario_note"] = (f"August, averaged over the three radar tracks; typical rain = median 7-day rain of the monsoon "
                        f"passes ({r_typ:.0f} mm); heavy rain = monsoon 95th percentile ({r_heavy:.0f} mm)")
out["runtime_s"] = round(time.time() - t0)
json.dump(out, open(f"{a.out}/learned_summary.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ("pixel_iou", "settlements", "ranking_auc", "permutation_importance_auc_drop",
                                      "scenarios_all_years_model")}, indent=1))
print("LEARNED_DONE", out["runtime_s"], "s")
