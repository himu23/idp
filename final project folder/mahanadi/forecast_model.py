"""Forecast the river flow at Naraj 1-3 days ahead from upstream flows and catchment rain (the prediction model).

    python mahanadi/forecast_model.py [--context data/mahanadi_context] [--out runs/_atlas/forecast]

A flood map is only as early as the flow forecast behind it. Water reaches Naraj from the Hirakud reach and the Tel
and Ong tributaries in about a day (travel_time.py), so today's upstream flows and the rain on the catchment between
Hirakud and Naraj say much about the next days. One gradient-boosted model per lead time learns the change in the
Naraj flow from:
  flows at Naraj, Tikarpara and below Hirakud today and on the two days before (log), their last-day changes,
  ERA5 rain over the catchment between Hirakud and Naraj (today, yesterday, 3- and 7-day sums), the day of the year.
Trained on 1997-2015 and tested on the monsoons (June-November) of 2016-2026, which it never saw. Baselines:
persistence (the flow stays as it is) and a linear routing model on the same flows. A second variant adds the rain of
the coming days as if forecast perfectly, an upper bound on what a rain forecast adds.
Flows are the GloFAS v4 reanalysis (the series the atlas is fitted on); with CWC records or Pravaah-type gauges the
same code trains on observed flows. Skill: Nash-Sutcliffe efficiency (NSE), Kling-Gupta efficiency (KGE), and hits
and false alarms for the flow crossing the high-flow level (monsoon 90th percentile) and the 2-year flood.
Outputs in <out>: forecast_summary.json, forecast_test.csv, forecast_naraj.png; <context>/rain_catchment.csv (cached)
"""
import argparse
import json
import os

import numpy as np
import pandas as pd
import requests

# ERA5 points over the catchment between Hirakud dam and Naraj (Tel, Ong, Jonk and the lower Mahanadi)
CATCHMENT_PTS = [(20.90, 83.00), (20.30, 83.30), (19.90, 83.00), (21.00, 83.60), (20.60, 84.00), (20.80, 84.60),
                 (20.40, 84.70), (20.60, 85.30)]
GAUGES = ("naraj", "tikarpara", "hirakud_below")
LEADS = (1, 2, 3)
TRAIN, TEST = (1997, 2015), (2016, 2026)  # the GloFAS series starts in 1997
WET = [6, 7, 8, 9, 10, 11]


def catchment_rain(context, end="2026-10-27"):
    path = f"{context}/rain_catchment.csv"
    if os.path.exists(path):
        return pd.read_csv(path, index_col="date", parse_dates=True)["rain_mm"]
    r = requests.get("https://archive-api.open-meteo.com/v1/archive", timeout=600, params=dict(
        latitude=",".join(str(p[0]) for p in CATCHMENT_PTS), longitude=",".join(str(p[1]) for p in CATCHMENT_PTS),
        start_date="1984-01-01", end_date=end, daily="precipitation_sum", timezone="Asia/Kolkata"))
    r.raise_for_status()
    rain = pd.concat([pd.Series(d["daily"]["precipitation_sum"], index=pd.to_datetime(d["daily"]["time"]), dtype=float)
                      for d in r.json()], axis=1).mean(axis=1).rename("rain_mm")
    rain.rename_axis("date").to_csv(path, float_format="%.2f")
    return rain


def features(Q, R, lead=0):
    """Predictors known on the issue day t (plus, with lead > 0, the rain of days t+1..t+lead as a perfect forecast)."""
    X = pd.DataFrame(index=Q.index)
    for c in GAUGES:
        lq = np.log1p(Q[c])
        for k in (0, 1, 2):
            X[f"{c}_t-{k}"] = lq.shift(k)
        X[f"{c}_change"] = lq - lq.shift(1)
    R = R.reindex(Q.index)
    X["rain_t"], X["rain_t-1"] = R, R.shift(1)
    X["rain_3d"], X["rain_7d"] = R.rolling(3).sum(), R.rolling(7).sum()
    for j in range(1, lead + 1):
        X[f"rain_t+{j}"] = R.shift(-j)
    doy = 2 * np.pi * Q.index.dayofyear / 365.25
    X["season_sin"], X["season_cos"] = np.sin(doy), np.cos(doy)
    return X


def fit(Q, R, lead, future_rain=False, years=TRAIN):
    """Gradient-boosted model of log(Q[t+lead] / Q[t]) at Naraj, fitted on the given years."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    X = features(Q, R, lead if future_rain else 0)
    y = np.log1p(Q.naraj.shift(-lead)) - np.log1p(Q.naraj)
    m = X.notna().all(axis=1) & y.notna() & (X.index.year >= years[0]) & (X.index.year <= years[1])
    model = HistGradientBoostingRegressor(max_iter=500, learning_rate=0.05, max_leaf_nodes=31, l2_regularization=1.0,
                                          random_state=0).fit(X[m], y[m])
    return model, list(X.columns)


def predict(model, cols, Q, R, lead, future_rain=False):
    X = features(Q, R, lead if future_rain else 0)[cols]
    ok = X.notna().all(axis=1)
    out = pd.Series(np.nan, index=Q.index)
    out[ok] = np.expm1(np.log1p(Q.naraj[ok]) + model.predict(X[ok]))
    return out


def skill(obs, pred, thresholds):
    ok = obs.notna() & pred.notna()
    o, p = obs[ok].values, pred[ok].values
    nse = 1 - ((p - o) ** 2).sum() / ((o - o.mean()) ** 2).sum()
    r = np.corrcoef(o, p)[0, 1]
    kge = 1 - np.sqrt((r - 1) ** 2 + (p.std() / o.std() - 1) ** 2 + (p.mean() / o.mean() - 1) ** 2)
    out = dict(nse=round(float(nse), 3), kge=round(float(kge), 3), mae_m3s=round(float(np.abs(p - o).mean())), n_days=int(ok.sum()))
    for name, thr in thresholds.items():
        hit, miss, fa = int(((o >= thr) & (p >= thr)).sum()), int(((o >= thr) & (p < thr)).sum()), int(((o < thr) & (p >= thr)).sum())
        out[name] = dict(threshold_m3s=round(thr), days_observed=hit + miss, hits=hit, misses=miss, false_alarms=fa,
                         pod=round(hit / max(hit + miss, 1), 3), far=round(fa / max(hit + fa, 1), 3),
                         csi=round(hit / max(hit + miss + fa, 1), 3))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--context", default="/home1/vineet/floodfm/data/mahanadi_context")
    ap.add_argument("--atlas", default="/home1/vineet/floodfm/runs/_atlas/build_r20")
    ap.add_argument("--out", default="/home1/vineet/floodfm/runs/_atlas/forecast")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    Q = pd.read_csv(f"{a.context}/discharge.csv", index_col="date", parse_dates=True)[list(GAUGES)].dropna()
    R = catchment_rain(a.context)
    AS = json.load(open(f"{a.atlas}/atlas_summary.json"))
    q90 = float(Q.naraj[Q.index.month.isin(WET)].quantile(0.9))
    thresholds = {"high_flow": q90, "two_year_flood": float(AS["gumbel"]["return_period_m3s"]["2"])}
    test = (Q.index.year >= TEST[0]) & (Q.index.year <= TEST[1]) & Q.index.month.isin(WET)

    # linear routing baseline: log Q_naraj[t+L] on today's logs at the three gauges and yesterday's at Tikarpara
    lin_cols = ["naraj_t-0", "tikarpara_t-0", "tikarpara_t-1", "hirakud_below_t-0", "hirakud_below_t-1"]
    X0 = features(Q, R)
    res, table = {}, pd.DataFrame(index=Q.index[test])
    table["observed"] = Q.naraj[test]
    for L in LEADS:
        obs = Q.naraj.shift(-L)
        tr = X0.notna().all(axis=1) & obs.notna() & (Q.index.year >= TRAIN[0]) & (Q.index.year <= TRAIN[1])
        A = np.c_[np.ones(tr.sum()), X0.loc[tr, lin_cols].values]
        coef, *_ = np.linalg.lstsq(A, np.log1p(obs[tr].values), rcond=None)
        ok = X0[lin_cols].notna().all(axis=1)
        lin = pd.Series(np.nan, index=Q.index)
        lin[ok] = np.expm1(np.c_[np.ones(ok.sum()), X0.loc[ok, lin_cols].values] @ coef)
        preds = {"persistence": Q.naraj, "linear_routing": lin}
        m, cols = fit(Q, R, L)
        preds["boosted"] = predict(m, cols, Q, R, L)
        m2, cols2 = fit(Q, R, L, future_rain=True)
        preds["boosted_with_rain_forecast"] = predict(m2, cols2, Q, R, L, future_rain=True)
        res[f"lead_{L}d"] = {k: skill(obs[test], p[test], thresholds) for k, p in preds.items()}
        for k, p in preds.items():
            table[f"{k}_lead{L}"] = p[test].round()
        table[f"observed_lead{L}"] = obs[test]
        print(f"lead {L} d:", {k: (v["nse"], v["two_year_flood"]["pod"], v["two_year_flood"]["far"]) for k, v in res[f"lead_{L}d"].items()},
              flush=True)
    table.to_csv(f"{a.out}/forecast_test.csv", float_format="%.0f")
    summary = dict(train_years=TRAIN, test_years=TEST, test_months=WET, gauges=GAUGES, catchment_rain_points=CATCHMENT_PTS,
                   thresholds_m3s={k: round(v) for k, v in thresholds.items()}, skill=res,
                   note="NSE/KGE on daily Naraj flow, June-November of the test years; event scores for the flow at the "
                        "lead time crossing each threshold. Flows: GloFAS v4 reanalysis.")
    json.dump(summary, open(f"{a.out}/forecast_summary.json", "w"), indent=1)
    figure(Q, table, a.out)
    print("FORECAST_DONE", flush=True)


def figure(Q, table, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    years = [2020, 2022]
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8), sharey=True)
    for ax, y in zip(axes, years):
        t = table[(table.index.year == y) & (table.index.month.isin([7, 8, 9]))]
        when = t.index
        ax.plot(when, t.observed / 1000, color="#0c3c6c", lw=2, label="Naraj flow (GloFAS)")
        ax.plot(when + pd.Timedelta(days=1), t.boosted_lead1 / 1000, color="#0c9ce4", lw=1.4, label="forecast 1 day ahead")
        ax.plot(when + pd.Timedelta(days=3), t.boosted_lead3 / 1000, color="#f08714", lw=1.4, label="forecast 3 days ahead")
        ax.plot(when + pd.Timedelta(days=3), t.persistence_lead3 / 1000, color="#94a3b8", lw=1, ls="--",
                label="persistence, 3 days")
        ax.set_title(f"Monsoon {y} (test year, not used in training)", fontsize=10)
        ax.grid(alpha=0.3)
        ax.tick_params(labelsize=8)
    axes[0].set_ylabel("Flow at Naraj (1000 m³/s)")
    axes[0].legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(f"{out}/forecast_naraj.png", dpi=150)


if __name__ == "__main__":
    main()
