"""Shared by infer.py and atlas_infer.py: load a radar-only Sen1Floods11 checkpoint and map a whole scene.

Sen1Floods11 radar is GRD sigma0 (GEE) while Planetary Computer gives RTC gamma0; we convert with
sigma0 ~= gamma0 + 10 log10(cos 37 deg) = gamma0 - 0.97 dB (incidence angle mid-swath).
"""
import json

import numpy as np
import torch

from floodfm.data import Normalizer, S1_BANDS, S2_BANDS
from floodfm.models import build, model_stats

HOME = "/home1/vineet/floodfm"
GAMMA_TO_SIGMA_DB = 10 * np.log10(np.cos(np.deg2rad(37.0)))


class Stats:
    def __init__(self, mean, std, s2_bands):
        full_m, full_s = dict(zip(S2_BANDS + S1_BANDS, mean)), dict(zip(S2_BANDS + S1_BANDS, std))
        self.m2 = np.array([full_m[b] for b in s2_bands] or [0], np.float32)[:, None, None]
        self.d2 = np.array([full_s[b] for b in s2_bands] or [1], np.float32)[:, None, None]
        self.m1 = np.array([full_m[b] for b in S1_BANDS], np.float32)[:, None, None]
        self.d1 = np.array([full_s[b] for b in S1_BANDS], np.float32)[:, None, None]


def load_model(run_dir):
    res = json.load(open(f"{run_dir}/results.json"))
    a, mods = res["args"], res["modalities"]
    assert not mods["s2"], "the Mahanadi maps use radar-only models (monsoon optical images are cloud-covered)"
    model = build(a["model"], s1=mods["s1"], s2=mods["s2"])
    model.load_state_dict(torch.load(f"{run_dir}/best.pt", map_location="cpu"))
    st = json.load(open(f"{HOME}/data/cache/stats_{a['protocol']}.json"))
    mean, std = model_stats(a["model"], st["mean"], st["std"])
    return model.cuda().eval(), Normalizer(Stats(mean, std, [])).cuda(), a["model"]


@torch.no_grad()
def predict_scene(model, norm, s1, tile=512, stride=448, batch=8):
    """Sliding-window water probability for a [2,H,W] sigma0-dB radar scene (NaN = no data)."""
    _, H, W = s1.shape
    ph, pw = max(H, tile), max(W, tile)
    pad = np.full((2, ph + tile, pw + tile), np.nan, np.float32)
    pad[:, :H, :W] = s1
    acc = np.zeros((ph + tile, pw + tile), np.float32)
    cnt = np.zeros_like(acc)
    ys = list(range(0, max(H - tile, 0) + 1, stride)) + [max(H - tile, 0)]
    xs = list(range(0, max(W - tile, 0) + 1, stride)) + [max(W - tile, 0)]
    win = np.outer(np.hanning(tile) + 0.05, np.hanning(tile) + 0.05).astype(np.float32)
    coords = [(y, x) for y in sorted(set(ys)) for x in sorted(set(xs))
              if np.isfinite(pad[1, y:y + tile, x:x + tile]).any()]  # skip windows with no radar at all
    for k in range(0, len(coords), batch):
        chunk = np.stack([pad[:, y:y + tile, x:x + tile] for y, x in coords[k:k + batch]])
        x_in = norm({"S1GRD": torch.from_numpy(chunk).cuda()})
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(x_in)
        p = logits.float().softmax(1)[:, 1].cpu().numpy()
        for (y, x), pi in zip(coords[k:k + batch], p):
            acc[y:y + tile, x:x + tile] += pi * win
            cnt[y:y + tile, x:x + tile] += win
    prob = acc[:H, :W] / np.maximum(cnt[:H, :W], 1e-6)
    prob[~np.isfinite(s1).all(0)] = np.nan
    return prob
