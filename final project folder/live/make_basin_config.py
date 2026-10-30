"""Write live/basins/<key>.json and live/data/<key>/ from a basin's atlas and impact results.

    python live/make_basin_config.py [mahanadi brahmani brahmaputra]

Reads results/atlas + results/impact for the Mahanadi and results/basins/<key>/{atlas,impact} for the other basins
(the files the server pipeline writes), so the live feed needs nothing but these small tables and the internet.
"""
import json
import os
import shutil
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "mahanadi"))
sys.path.insert(0, HERE)
from basins import BASINS  # noqa: E402
from levels import baseline, level_flows  # noqa: E402

TABLES = ("impact_curve.csv", "settlement_thresholds.csv", "road_cut_flows.csv", "facility_thresholds.csv")
WINDOW = {"Q_same_day": 1, "Q_prev_day": 1, "Q_max_3d": 3, "Q_max_5d": 5, "Q_max_7d": 7}


def result_dirs(key):
    if key == "mahanadi":
        return os.path.join(ROOT, "results", "atlas"), os.path.join(ROOT, "results", "impact")
    base = os.path.join(ROOT, "results", "basins", key)
    return os.path.join(base, "atlas"), os.path.join(base, "impact")


def make(key):
    atlas, impact = result_dirs(key)
    AS = json.load(open(os.path.join(atlas, "atlas_summary.json")))
    curve = pd.read_csv(os.path.join(impact, "impact_curve.csv"))
    data = os.path.join(HERE, "data", key)
    os.makedirs(data, exist_ok=True)
    for t in TABLES:
        if os.path.exists(os.path.join(impact, t)):
            shutil.copy(os.path.join(impact, t), os.path.join(data, t))
    b = BASINS[key]
    # the ordinary monsoon: the flow measure exceeded on a quarter of the flood-season days (from the gauge's record)
    q = pd.read_csv(os.path.join(data, "discharge.csv"), index_col="date", parse_dates=True)[b["gauge"]].dropna()
    w = WINDOW.get(AS["predictor"], 1)
    qm = (q.shift(1) if AS["predictor"] == "Q_prev_day" else q).rolling(w, min_periods=1).max()
    q_base = float(qm[qm.index.month.isin(b["wet"])].quantile(0.75))
    base = baseline(curve, q_base)
    cfg = dict(key=key, **{k: b[k] for k in ("name", "state", "river", "gauge_name", "bbox", "gauge", "gauges", "rain_pts",
                                            "districts", "sachet")},
               predictor=AS["predictor"], predictor_days=WINDOW.get(AS["predictor"], 1),
               predictor_lag=1 if AS["predictor"] == "Q_prev_day" else 0,
               design_flows_m3s={int(k): round(v) for k, v in AS["gumbel"]["return_period_m3s"].items()},
               largest_seen_m3s=round(AS["largest_observed_predictor_m3s"]),
               high_flow_m3s=AS["validation"]["high_flow_passes"].get("q90_threshold_m3s"),
               baseline_m3s=round(q_base), baseline=base, level_flows_m3s=level_flows(curve, base),
               atlas_passes=AS["n_passes"], atlas_threshold=AS["threshold"],
               routing="hospital_people_cut_off" in curve.columns,
               tables={t[:-4]: f"data/{key}/{t}" for t in TABLES if os.path.exists(os.path.join(data, t))},
               sources=["glofas", "rain", "sachet", "cwc", "sentinel1"],
               forecast_model=key == "mahanadi")
    os.makedirs(os.path.join(HERE, "basins"), exist_ok=True)
    json.dump(cfg, open(os.path.join(HERE, "basins", f"{key}.json"), "w"), indent=1)
    print(key, "baseline", round(q_base), "m3/s", base, "levels start at", cfg["level_flows_m3s"], "m3/s;", len(cfg["tables"]), "tables")


if __name__ == "__main__":
    for k in sys.argv[1:] or ["mahanadi"]:
        make(k)
