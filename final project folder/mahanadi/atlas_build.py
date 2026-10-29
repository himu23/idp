"""Mahanadi-delta flood atlas and discharge-to-inundation model (flood-atlas step 3).

    python mahanadi/atlas_build.py --prob <runs/_atlas/prob> --inventory <data/mahanadi_atlas/inventory.csv>
                                   --context <data/mahanadi_context> --jrc <.../jrc_occurrence.tif> --out <dir>
                                   [--model terramind]

Everything is on the 20 m atlas grid (pixel = 400 m2).
1. Normal water per year = water in >= 50 % of that year's Feb-Mar (dry season) passes, or JRC occurrence >= 50 %,
   or river bed (WorldCover water/sand joined to the main channels; the bed going under is not a flood).
2. Flood on a monsoon pass (Jun-Nov) = water AND NOT normal water of that year.
3. Flood frequency = flooded passes / valid monsoon passes, per pixel.
4. Discharge predictor: GloFAS v4 flow at Naraj (same day, previous day, or recent peak); chosen by the Spearman
   correlation with the flooded fraction of each pass. Rain predictor: ERA5 3-7 day rain over the delta, same rule.
5. Per-pixel trigger discharge: the threshold theta that best separates the pixel's wet and dry monsoon
   observations under the rule "flooded if predictor >= theta" (ties -> lower theta, i.e. warn earlier).
   Codes: 0 = wet at any flow; 1e6 = never flooded in the record; NaN = fewer than 10 observations.
   River-driven score = AUC of the predictor between the pixel's wet and dry observations (0.5 = unrelated to
   river flow, e.g. paddy or rain water-logging; ~1 = floods only at high river flow).
6. Leave-one-year-out test: fit on the other years, predict each pass of the held-out year, compare with the observed
   flood map, per pixel and per settlement. Methods: trigger map (flow only); analogs (flood where >= half of the 7
   training passes most similar in flow, or in flow and rain, were flooded); climatology (frequency >= 50 %).
7. Design floods: Gumbel fit to GloFAS annual maxima at Naraj 1984-2025; scenario maps for T = 2...100 years.
"""
import argparse
import glob
import json
import os

import numpy as np
import pandas as pd
import rasterio
from scipy.stats import spearmanr

ap = argparse.ArgumentParser()
ap.add_argument("--prob", required=True)
ap.add_argument("--inventory", required=True, nargs="+")
ap.add_argument("--context", required=True)
ap.add_argument("--jrc", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--model", default="mean", help="terramind | unet | mean (average of the two radar models)")
ap.add_argument("--thr", type=float, default=0.5, help="water if probability >= thr (chosen on Sen1Floods11 validation)")
ap.add_argument("--min_cov", type=float, default=0.5)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
PIX_KM2 = 400 / 1e6
NEVER, ALWAYS = 1e6, 0.0

# ---------------------------------------------------------------- passes and discharge
inv = pd.concat([pd.read_csv(f) for f in a.inventory]).drop_duplicates("name", keep="last").set_index("name")
MEMBERS = ["terramind", "unet"] if a.model == "mean" else [a.model]
names = set.intersection(*[{os.path.basename(f)[:-len(f"_{m}.tif")] for f in glob.glob(f"{a.prob}/S1_*_{m}.tif")}
                           for m in MEMBERS])
files = {n: [f"{a.prob}/{n}_{m}.tif" for m in MEMBERS] for n in names}
THR = int(round(a.thr * 254))
inv = inv[inv.index.isin(files) & (inv.coverage >= a.min_cov)].copy()
inv["date"] = pd.to_datetime(inv["date"])
inv["year"], inv["month"] = inv.date.dt.year, inv.date.dt.month
inv = inv.sort_values("date")
Q = pd.read_csv(f"{a.context}/discharge.csv", index_col="date", parse_dates=True)["naraj"]
preds = {"Q_same_day": Q, "Q_prev_day": Q.shift(1), "Q_max_3d": Q.rolling(3).max(), "Q_max_5d": Q.rolling(5).max(),
         "Q_max_7d": Q.rolling(7).max()}
for k, s_ in preds.items():
    inv[k] = s_.reindex(inv.date).values
# Local rain (ERA5 daily, IST days, delta mean). The largest flood extents in a first atlas (Sep 2018, Sep 2021)
# came with moderate Naraj flows and 100-160 mm/day of rain from depressions, so rain is tested as a second driver.
rain = pd.read_csv(f"{a.context}/rain.csv", index_col="date", parse_dates=True)["rain_mm"]
rpreds = {"R_3d": rain.rolling(3).sum(), "R_prev_3d": rain.shift(1).rolling(3).sum(), "R_5d": rain.rolling(5).sum(),
          "R_7d": rain.rolling(7).sum()}
for k, s_ in rpreds.items():
    inv[k] = s_.reindex(inv.date).values

with rasterio.open(next(iter(files.values()))[0]) as src:
    prof = src.profile
    H, W = src.height, src.width
with rasterio.open(a.jrc) as src:  # 10 m -> 20 m (mean of 2 x 2)
    j = src.read(1).astype(np.float32)
jrc = j[:H * 2, :W * 2].reshape(H, 2, W, 2).mean(axis=(1, 3))


EDGE_PX = 150  # 3 km


def edge_band(nod):
    """Pixels within 3 km of the pass's data edge. A first atlas showed a 3 km wide diagonal band of false
    'floods' along one track's swath edge (border noise, and model windows half outside the data)."""
    if not nod.any():
        return np.zeros_like(nod)
    from scipy import ndimage
    d = ndimage.distance_transform_edt(~nod[::5, ::5]) * 5  # at 100 m, in 20 m pixels
    return np.repeat(np.repeat(d, 5, 0), 5, 1)[:H, :W] <= EDGE_PX


def load(names):
    """Water probability x 254 (uint8, 255 = no data or within 3 km of the swath edge) per pass;
    for 'mean' the average of the member models."""
    arr = np.empty((len(names), H, W), np.uint8)
    for i, n in enumerate(names):
        ps = []
        for f in files[n]:
            with rasterio.open(f) as src:
                ps.append(src.read(1))
        nod = np.any([p == 255 for p in ps], axis=0)
        if len(ps) == 1:
            arr[i] = ps[0]
        else:
            arr[i] = np.where(nod, 255, np.round(np.mean([p.astype(np.float32) for p in ps], axis=0))).astype(np.uint8)
        arr[i][edge_band(nod)] = 255
    return arr


def save(name, arr, dtype, nodata=None, desc=None):
    p = dict(prof, dtype=dtype, nodata=nodata, count=arr.shape[0] if arr.ndim == 3 else 1, compress="deflate")
    with rasterio.open(f"{a.out}/{name}.tif", "w", **p) as dst:
        dst.write(arr.astype(dtype) if arr.ndim == 3 else arr.astype(dtype)[None])
        if desc:
            dst.update_tags(description=desc)


# ---------------------------------------------------------------- 1. normal water per year
dry = inv[inv.month.isin([2, 3])]
normal = {}
all_dry = load(list(dry.index))
dv, dw = all_dry != 255, (all_dry != 255) & (all_dry >= THR)
pooled = (dw.sum(0) >= 0.5 * np.maximum(dv.sum(0), 1)) & (dv.sum(0) >= 4)
for y in sorted(inv.year.unique()):
    sel = (dry.year == y).values
    if sel.sum() >= 4:
        nv, nw = dv[sel].sum(0), dw[sel].sum(0)
        normal[y] = np.where(nv >= 3, nw >= 0.5 * nv, pooled) | (jrc >= 50)
    else:
        normal[y] = pooled | (jrc >= 50)
del all_dry, dv, dw
print("dry passes", len(dry), "years with own dry reference:",
      [int(y) for y in normal if (dry.year == y).sum() >= 4], flush=True)

# River bed: dry-season sand bars are not water in Feb-Mar, so without this the bed going under at every
# monsoon counts as "flood" (in a first run 2/3 of the 2-year flood area was WorldCover sand or water).
# Bed = WorldCover water (80) or bare/sand (60) or normal water, in components that hold > 1 km2 of normal water.
from scipy import ndimage  # noqa: E402
with rasterio.open(f"{a.context}/grid20_worldcover.tif") as src:
    wc = src.read(1)
latest = normal[max(normal)]
lab, nlab = ndimage.label(latest | (wc == 80) | (wc == 60), structure=np.ones((3, 3)))
nw_in = ndimage.sum(latest, lab, np.arange(1, nlab + 1))
bed = np.isin(lab, np.where(nw_in * PIX_KM2 > 1.0)[0] + 1)
del lab
for y in normal:
    normal[y] = normal[y] | bed
print(f"river bed (channels + sand bars): {bed.sum() * PIX_KM2:.0f} km2", flush=True)

# ---------------------------------------------------------------- 2-3. monsoon floods and frequency
mon = inv[inv.month.isin([6, 7, 8, 9, 10, 11])].copy()
P = load(list(mon.index))
V = P != 255
WET = V & (P >= THR)
del P
NORM = np.stack([normal[y] for y in mon.year])  # per pass: normal water of that year
FL = WET & ~NORM
VL = V & ~NORM  # pixels that can flood (valid, not normal water)
mon["valid_land_km2"] = VL.sum((1, 2)) * PIX_KM2
mon["flood_km2"] = FL.sum((1, 2)) * PIX_KM2
mon["water_km2"] = WET.sum((1, 2)) * PIX_KM2
mon["flood_frac"] = mon.flood_km2 / mon.valid_land_km2
n_obs, n_fl = VL.sum(0), FL.sum(0)
freq = np.where(n_obs >= 10, n_fl / np.maximum(n_obs, 1), np.nan)
save("flood_frequency", np.where(np.isfinite(freq), np.round(freq * 100), 255), "uint8", 255,
     "percent of valid Jun-Nov passes flooded (255 = <10 observations)")
save("flood_count", n_fl, "uint16", None, "number of flooded monsoon passes")
save("monsoon_obs", n_obs, "uint16", None, "number of valid monsoon passes (excluding normal water)")
save("normal_water_latest", normal[max(normal)], "uint8", None, "normal water of the latest year + river bed")
save("river_bed", bed, "uint8", None, "river bed: channels and sand bars (WorldCover 60/80 joined to > 1 km2 of normal water)")
years = sorted(mon.year.unique())
peryear = np.stack([np.where(n >= 3, f / np.maximum(n, 1), np.nan) for f, n in
                    ((FL[(mon.year == y).values].sum(0), VL[(mon.year == y).values].sum(0)) for y in years)])
save("flood_frequency_by_year", np.where(np.isfinite(peryear), np.round(peryear * 100), 255), "uint8", 255,
     "bands = " + ",".join(map(str, years)))
max_ext = np.stack([FL[(mon.year == y).values].any(0) for y in years])
save("max_extent_by_year", max_ext, "uint8", None, "bands = " + ",".join(map(str, years)))

# ---------------------------------------------------------------- 4. discharge predictor
ok = mon.valid_land_km2 > 0.6 * mon.valid_land_km2.max()
corr = {k: float(spearmanr(mon.loc[ok, k], mon.loc[ok, "flood_frac"]).statistic) for k in preds}
best = max(corr, key=corr.get)
mon["q"] = mon[best]
print("Spearman(flood fraction, predictor):", {k: round(v, 3) for k, v in corr.items()}, "->", best, flush=True)
rcorr = {k: float(spearmanr(mon.loc[ok, k], mon.loc[ok, "flood_frac"], nan_policy="omit").statistic) for k in rpreds}
best_r = max(rcorr, key=rcorr.get)
mon["r"] = mon[best_r].fillna(0)
print("Spearman(flood fraction, rain):", {k: round(v, 3) for k, v in rcorr.items()}, "->", best_r, flush=True)


# ---------------------------------------------------------------- 5. per-pixel trigger discharge
# Only pixels that flooded at least once can get a finite trigger; the fit runs on those columns only
# (row gathers of a pixels-by-passes stack, small integer counters).
cand = (n_fl > 0) & (n_obs >= 10)
FLc, VLc = FL[:, cand], VL[:, cand]
print(f"trigger fit on {cand.sum():,} candidate pixels ({cand.mean():.0%})", flush=True)


def fit(idx):
    """Trigger discharge and river-driven AUC (full grids) from the passes idx (row indices into mon)."""
    q = mon.q.values[idx]
    order = np.argsort(q, kind="stable")
    qs, rows_ = q[order], idx[order]
    nc = FLc.shape[1]
    wet_below = np.zeros(nc, np.int32)
    dry_below = np.zeros(nc, np.int32)
    tot_wet = np.zeros(nc, np.int32)
    tot_dry = np.zeros(nc, np.int32)
    for r in rows_:
        tot_wet += FLc[r]
        tot_dry += VLc[r] & ~FLc[r]
    auc = np.zeros(nc, np.int64)
    best_err = tot_dry.copy()  # k = 0: predict wet for every pass
    best_k = np.zeros(nc, np.int32)
    for k, r in enumerate(rows_):
        if k > 0 and qs[k] > qs[k - 1]:
            err = wet_below + (tot_dry - dry_below)
            better = err < best_err
            best_err = np.where(better, err, best_err)
            best_k = np.where(better, k, best_k)
        w = FLc[r]
        auc += np.where(w, dry_below, 0)
        wet_below += w
        dry_below += VLc[r] & ~w
    better = wet_below < best_err  # k = N: predict dry for every pass
    best_k = np.where(better, len(qs), best_k)
    edges = np.concatenate([[ALWAYS], (qs[:-1] + qs[1:]) / 2, [NEVER]])
    th_c = edges[best_k].astype(np.float32)
    th_c[(tot_wet + tot_dry) < 10] = np.nan
    auc_c = np.where((tot_wet > 0) & (tot_dry > 0), auc / np.maximum(tot_wet.astype(np.int64) * tot_dry, 1), np.nan)
    nobs = np.zeros((H, W), np.int32)
    for r in idx:
        nobs += VL[r]
    theta = np.where(nobs >= 10, NEVER, np.nan).astype(np.float32)
    theta[cand] = th_c
    aucf = np.full((H, W), np.nan, np.float32)
    aucf[cand] = auc_c
    return theta, aucf


allidx = np.arange(len(mon))
theta, auc = fit(allidx)
save("trigger_discharge", theta, "float32", None,
     f"Naraj {best} (m3/s) at which the pixel floods; 0 = wet at any flow, 1e6 = never flooded, NaN = <10 obs")
save("river_driven_auc", np.where(np.isfinite(auc), np.round(auc * 100), 255), "uint8", 255,
     "AUC x100 of discharge between wet and dry observations (50 = unrelated to river flow)")


# ---------------------------------------------------------------- 6. leave-one-year-out test
def counts(pred, obs, valid):
    return np.array([(pred & obs & valid).sum(), (pred & ~obs & valid).sum(), (~pred & obs & valid).sum()])


q90 = float(Q[(Q.index.month >= 6) & (Q.index.month <= 11)].quantile(0.9))
# Settlements (same rule as impact_exposure.py): >= 1,000 people/km2, dilated 1 px, >= 200 people. A warning is
# about villages, so the held-out test also asks: was a settlement with >= 10 % of its people on flooded land flagged?
from scipy import ndimage  # noqa: E402
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


METHODS = ("model", "aq", "aqr", "clim")  # trigger map, analog on flow, analog on flow + rain, climatology
sett = {m: np.zeros((3, 3), int) for m in METHODS}  # rows: all, high flow, high rain; cols: hit, miss, false alarm
r90 = float(rpreds[best_r][(rpreds[best_r].index.month >= 6) & (rpreds[best_r].index.month <= 11)].quantile(0.9))


def analog(train, qi, ri, use_r, k=7, frac=False):
    """Flood where >= half of the k most similar training passes (flow rank, and rain rank) were flooded
    (frac=True: the flooded fraction of the analogs, for ranking scores)."""
    qt, rt = mon.q.values[train], mon.r.values[train]
    d = (np.searchsorted(np.sort(qt), qt) - np.searchsorted(np.sort(qt), qi)) / len(qt)
    d = d ** 2
    if use_r:
        d = d + ((np.searchsorted(np.sort(rt), rt) - np.searchsorted(np.sort(rt), ri)) / len(rt)) ** 2
    rows_ = train[np.argsort(d, kind="stable")[:k]]
    f = np.zeros((H, W), np.int16)
    v = np.zeros((H, W), np.int16)
    for r_ in rows_:
        f += FL[r_]
        v += VL[r_]
    if frac:
        return np.where(v >= 3, f / np.maximum(v, 1), 0.0)
    return (v >= 3) & (2 * f >= v)
fold_theta = {}
# Ranking skill: a warning map ranks land by how likely it floods; ROC AUC on a sample of each held-out pass's pixels
rng = np.random.default_rng(0)
auc_y, auc_s, auc_hf = [], {"model": [], "aqr": [], "clim": []}, []
fl_year = {y: FL[(mon.year == y).values].sum(0, dtype=np.int32) for y in years}
vl_year = {y: VL[(mon.year == y).values].sum(0, dtype=np.int32) for y in years}
fl_tot, vl_tot = sum(fl_year.values()), sum(vl_year.values())
rows = []
for y in years:
    test = np.where(mon.year.values == y)[0]
    train = np.where(mon.year.values != y)[0]
    if len(test) == 0 or len(train) < 50:
        continue
    th, _ = fit(train)
    fold_theta[y] = th
    f_tr, v_tr = fl_tot - fl_year[y], vl_tot - vl_year[y]
    clim = (v_tr >= 10) & (f_tr >= 0.5 * v_tr)
    th_score = np.where(np.isfinite(th), -th.astype(np.float64), -2e6)
    fr_train = np.where(v_tr >= 10, f_tr / np.maximum(v_tr, 1), 0.0)
    for i in test:
        qi, ri = mon.q.values[i], mon.r.values[i]
        pred = np.isfinite(th) & (th <= qi)
        pix = np.flatnonzero(VL[i])
        if len(pix):
            pix = rng.choice(pix, size=min(len(pix), 40000), replace=False)
            auc_y.append(FL[i].ravel()[pix])
            auc_s["model"].append(th_score.ravel()[pix])
            auc_s["clim"].append(fr_train.ravel()[pix])
            auc_s["aqr"].append(analog(train, qi, ri, True, frac=True).ravel()[pix])
            auc_hf.append(np.full(len(pix), qi >= q90))
        preds_i = {"model": pred, "aq": analog(train, qi, ri, False), "aqr": analog(train, qi, ri, True), "clim": clim}
        obs_f, ok_s = flagged(FL[i], VL[i])
        for key, m in preds_i.items():
            pf, _ = flagged(m, VL[i])
            c3 = np.array([(pf & obs_f & ok_s).sum(), (~pf & obs_f & ok_s).sum(), (pf & ~obs_f & ok_s).sum()])
            sett[key][0] += c3
            if qi >= q90:
                sett[key][1] += c3
            if ri >= r90:
                sett[key][2] += c3
        rec = dict(name=mon.index[i], year=int(y), q=float(qi), r=float(ri), high_flow=bool(qi >= q90),
                   high_rain=bool(ri >= r90), obs_km2=float(FL[i].sum() * PIX_KM2),
                   pred_km2=float((pred & VL[i]).sum() * PIX_KM2), aqr_km2=float((preds_i["aqr"] & VL[i]).sum() * PIX_KM2))
        for key, m in preds_i.items():
            rec.update({f"{key}_{k}": int(v) for k, v in zip(("tp", "fp", "fn"), counts(m, FL[i], VL[i]))})
        rows.append(rec)
    print("LOYO", y, len(test), "passes", flush=True)
loyo = pd.DataFrame(rows)
loyo.to_csv(f"{a.out}/loyo_passes.csv", index=False)


def iou(df, p):
    tp, fp, fn = df[f"{p}_tp"].sum(), df[f"{p}_fp"].sum(), df[f"{p}_fn"].sum()
    return dict(iou=round(tp / max(tp + fp + fn, 1), 3), precision=round(tp / max(tp + fp, 1), 3),
                recall=round(tp / max(tp + fn, 1), 3))


def block(df):
    return {"n": len(df), "model": iou(df, "model"), "analog_flow": iou(df, "aq"), "analog_flow_rain": iou(df, "aqr"),
            "climatology": iou(df, "clim")}


val = {"all_monsoon_passes": block(loyo),
       "high_flow_passes": {**block(loyo[loyo.high_flow]), "q90_threshold_m3s": round(q90)},
       "high_rain_passes": {**block(loyo[loyo.high_rain]), "r90_threshold_mm": round(r90, 1), "rain_predictor": best_r},
       "per_year": {int(y): {**block(g), "max_obs_km2": round(g.obs_km2.max(), 1)} for y, g in loyo.groupby("year")}}
c_area = loyo[["obs_km2", "pred_km2"]].corr().iloc[0, 1]
val["area_correlation"] = round(float(c_area), 3)
from sklearn.metrics import roc_auc_score  # noqa: E402
yy, hf_ = np.concatenate(auc_y), np.concatenate(auc_hf)
val["ranking_auc"] = {sub: {m: round(float(roc_auc_score(yy[sel], np.concatenate(v)[sel])), 3) for m, v in auc_s.items()}
                      for sub, sel in (("all_passes", np.ones(len(yy), bool)), ("high_flow_passes", hf_))
                      if yy[sel].any() and (~yy[sel]).any()}
val["ranking_auc"]["note"] = ("pixels of each held-out pass ranked by -trigger discharge (model), analog flooded fraction "
                              "(flow + rain) and training-year flood frequency (climatology); 0.5 = no skill")


def skill(c3):
    h, m, f = (int(v) for v in c3)
    return dict(hits=h, misses=m, false_alarms=f, POD=round(h / max(h + m, 1), 3), FAR=round(f / max(h + f, 1), 3),
                CSI=round(h / max(h + m + f, 1), 3))


val["settlements"] = {"rule": "settlement flagged when >= 10 % of its people are on flooded land; scored on passes "
                               "seeing >= 80 % of its people", "settlements": int(len(sid)),
                      **{sub: {"model": skill(sett["model"][j]), "analog_flow": skill(sett["aq"][j]),
                               "analog_flow_rain": skill(sett["aqr"][j]), "climatology": skill(sett["clim"][j])}
                         for j, sub in enumerate(("all_passes", "high_flow_passes", "high_rain_passes"))}}
if fold_theta:
    save("trigger_discharge_loyo", np.stack([fold_theta[y] for y in sorted(fold_theta)]), "float32", None,
         "bands = held-out year " + ",".join(map(str, sorted(fold_theta))) + " (trigger fitted without that year)")

# ---------------------------------------------------------------- 7. design floods (Gumbel, method of moments)
ann = Q[Q.index.year <= 2025].groupby(Q.index.year[Q.index.year <= 2025]).max()
beta = ann.std() * np.sqrt(6) / np.pi
mu = ann.mean() - 0.5772 * beta
rp = {T: float(mu - beta * np.log(-np.log(1 - 1 / T))) for T in (2, 5, 10, 25, 50, 100)}
qmax_obs = float(mon.q.max())
scen = {}
land = ~normal[max(normal)]
for T, qT in rp.items():
    m = np.isfinite(theta) & (theta <= qT) & land
    scen[T] = m
    print(f"T={T:>3} y  Q={qT:,.0f} m3/s ({qT / 2831.7:.1f} lakh cusec)  flood {m.sum() * PIX_KM2:.0f} km2"
          + ("  [above the largest observed flow: lower bound]" if qT > qmax_obs else ""), flush=True)
save("scenarios_return_period", np.stack([scen[T] for T in rp]), "uint8", None,
     "bands = T " + ",".join(map(str, rp)) + " years (Gumbel on GloFAS Naraj annual maxima 1984-2025)")

# compound scenario: 5-year flow with heavy local rain (95th percentile of the monsoon rain predictor), from analogs
r95 = float(rpreds[best_r][(rpreds[best_r].index.month >= 6) & (rpreds[best_r].index.month <= 11)].quantile(0.95))
heavy = analog(allidx, rp[5], r95, True) & land
save("scenario_heavy_rain", heavy, "uint8", None,
     f"5-year flow ({rp[5]:.0f} m3/s) with heavy local rain ({best_r} = {r95:.0f} mm, 95th percentile of Jun-Nov): analog map")
print(f"5-yr flow + heavy rain ({r95:.0f} mm {best_r}): flood {heavy.sum() * PIX_KM2:.0f} km2", flush=True)

# ---------------------------------------------------------------- outputs
np.savez_compressed(f"{a.out}/flood_library.npz", fl=np.packbits(FL.reshape(len(mon), -1), axis=1),
                    vl=np.packbits(VL.reshape(len(mon), -1), axis=1), q=mon.q.values, r=mon.r.values,
                    names=np.array(mon.index), shape=np.array([H, W]))
big = mon[mon.coverage >= 0.85].flood_km2.idxmax()  # largest flood seen on a near-complete pass
k = list(mon.index).index(big)
save("observed_largest_flood", np.where(VL[k] | FL[k], FL[k], 255), "uint8", 255,
     f"flood on pass {big} ({mon.loc[big, 'date'].date()}, {mon.loc[big, 'flood_km2']:.0f} km2); 255 = no data / normal water")
mon.drop(columns=[c for c in mon.columns if c.startswith("Q_")]).to_csv(f"{a.out}/atlas_passes.csv")
inv.to_csv(f"{a.out}/atlas_inventory_used.csv")
summary = dict(
    model=a.model, threshold=a.thr, n_passes=int(len(inv)), n_monsoon=int(len(mon)), n_dry=int(len(dry)), years=[int(y) for y in years],
    predictor=best, predictor_spearman=corr, rain_predictor=best_r, rain_spearman=rcorr, validation=val,
    gumbel=dict(mu=round(float(mu)), beta=round(float(beta)), n_years=int(len(ann)),
                return_period_m3s={int(k): round(v) for k, v in rp.items()},
                return_period_lakh_cusec={int(k): round(v / 2831.7, 2) for k, v in rp.items()}),
    largest_observed_predictor_m3s=round(qmax_obs),
    scenario_flood_km2={int(T): round(float(m.sum() * PIX_KM2), 1) for T, m in scen.items()},
    heavy_rain_scenario=dict(q_m3s=round(rp[5]), rain_mm=round(r95), rain_predictor=best_r,
                             flood_km2=round(float(heavy.sum() * PIX_KM2), 1)),
    flooded_ever_km2=round(float((n_fl > 0).sum() * PIX_KM2), 1),
    flooded_20pct_km2=round(float((np.nan_to_num(freq) >= 0.2).sum() * PIX_KM2), 1),
    river_driven_km2=round(float((np.nan_to_num(auc) >= 0.75).sum() * PIX_KM2), 1),
    river_bed_km2=round(float(bed.sum() * PIX_KM2), 1),
    top_passes=mon.sort_values("flood_km2", ascending=False).head(10)[["date", "flood_km2", "q"]].astype(str)
    .to_dict("records"))
json.dump(summary, open(f"{a.out}/atlas_summary.json", "w"), indent=1, default=str)
print(json.dumps({k: summary[k] for k in ("n_passes", "n_monsoon", "predictor", "validation", "scenario_flood_km2")},
                 indent=1, default=str))
print("ATLAS_BUILD_DONE")
