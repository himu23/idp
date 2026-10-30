"""Collect the 10 m- and 20 m-trained radar pairs over three seeds (report Appendix B).

    env/bin/python code/scripts/summarise_r20_seeds.py      (after server/run_r20_seeds.sh)

Seed 0 comes from runs/_analysis/radar20m.json and radar20m_r20.json, seeds 1 and 2 from the logs of
scripts/test_resolution.py. "avg20" is the fused pair on the 20 m overview at threshold 0.5, "cal" the same with the
threshold chosen on validation. Writes runs/_analysis/radar20m_seeds.json.
"""
import json
import re

import numpy as np

H = "/home1/vineet/floodfm"


def from_log(path):
    log = open(path).read()
    m = re.search(r"^mean\s+avg20\s+IoU ([0-9.]+)", log, re.M)
    c = re.search(r"chosen threshold ([0-9.]+): test IoU ([0-9.]+)", log)
    return dict(avg20=float(m.group(1)), thr=float(c.group(1)), cal=float(c.group(2)))


r10, r20 = json.load(open(f"{H}/runs/_analysis/radar20m.json")), json.load(open(f"{H}/runs/_analysis/radar20m_r20.json"))
out = {"10m": {"0": dict(avg20=r10["mean"]["avg20"], thr=r10["threshold"], cal=r10["calibrated_test_iou"])},
       "20m": {"0": dict(avg20=r20["mean"]["avg20"], thr=r20["threshold"], cal=r20["calibrated_test_iou"])}}
for s in ("1", "2"):
    out["10m"][s] = from_log(f"{H}/logs/test_resolution_s{s}.log")
    out["20m"][s] = from_log(f"{H}/logs/test_resolution_s{s}_r20.log")
summ = {}
for k in ("10m", "20m"):
    a = np.array([v["avg20"] for v in out[k].values()])
    c = np.array([v["cal"] for v in out[k].values()])
    summ[k] = dict(avg20_mean=round(float(a.mean()), 4), avg20_sd=round(float(a.std()), 4),
                   cal_mean=round(float(c.mean()), 4), cal_sd=round(float(c.std()), 4))
gains = [out["20m"][s]["cal"] - out["10m"][s]["cal"] for s in out["10m"]]
summ.update(gain_cal_mean=round(float(np.mean(gains)), 4), wins_all=bool(all(g > 0 for g in gains)))
out["summary"] = summ
json.dump(out, open(f"{H}/runs/_analysis/radar20m_seeds.json", "w"), indent=1)
print(json.dumps(out, indent=1))
