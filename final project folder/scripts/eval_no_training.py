"""Methods that receive no training from us, scored with the shared evaluator.

  otsu_vh        per-chip Otsu threshold on Sentinel-1 VH (dB), darker = water
  mndwi          (Green - SWIR1)/(Green + SWIR1) > 0   (Sentinel-2 B03, B11)
  ndwi           (Green - NIR)/(Green + NIR) > 0       (Sentinel-2 B03, B08)
  prithvi_published  IBM/NASA Prithvi-EO-2.0-300M-TL-Sen1Floods11 checkpoint, used as released
                 (true zero-shot for us; NOTE it was trained on the official Sen1Floods11
                 train split, which contains 40 India chips, so its India score is not unseen)

Writes runs/<protocol>_<method>/results.json + prob_*.npy, same format as floodfm.train.
"""
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, sys.argv[1])
from floodfm.data import Cache, chip_event, RADAR_NODATA_DB, S2_BANDS  # noqa: E402
from floodfm.metrics import evaluate  # noqa: E402

HOME = "/home1/vineet/floodfm"
cache = Cache(f"{HOME}/data/cache")


def index_prob(i, a, b):
    s2 = cache.s2[i].astype(np.float32)
    g, x = s2[S2_BANDS.index(a)], s2[S2_BANDS.index(b)]
    ok = (g > 0) & (x > 0)
    idx = np.where(ok, (g - x) / np.maximum(g + x, 1e-6), -1.0)
    return ((idx + 1) / 2 * 255).round().clip(0, 255).astype(np.uint8)  # 0.5 <-> index 0


def otsu_prob(i):
    from skimage.filters import threshold_otsu
    vh = cache.s1[i][1].astype(np.float32)
    ok = np.isfinite(vh) & (vh > RADAR_NODATA_DB)
    out = np.zeros(vh.shape, np.uint8)
    if ok.sum() > 100:
        t = threshold_otsu(vh[ok])
        out[ok & (vh < t)] = 255
    return out


def published_prithvi():
    from terratorch.models import EncoderDecoderFactory
    from terratorch.datamodules import sen1floods11 as dm  # MEANS/STDS used by the released config
    net = EncoderDecoderFactory().build_model(
        task="segmentation", backbone="prithvi_eo_v2_300_tl", backbone_pretrained=False,
        backbone_bands=["BLUE", "GREEN", "RED", "NIR_NARROW", "SWIR_1", "SWIR_2"], backbone_img_size=512,
        decoder="UperNetDecoder", decoder_channels=256, num_classes=2, rescale=True, head_dropout=0.1,
        necks=[{"name": "SelectIndices", "indices": [5, 11, 17, 23]}, {"name": "ReshapeTokensToImage"},
               {"name": "LearnedInterpolateToPyramidal"}])
    ck = torch.load(f"{HOME}/data/prithvi_tl_sen1floods11/Prithvi-EO-V2-300M-TL-Sen1Floods11.pt",
                    map_location="cpu", weights_only=False)["state_dict"]
    sd = {k[len("model."):]: v for k, v in ck.items() if k.startswith("model.")}
    missing, unexpected = net.load_state_dict(sd, strict=False)
    print("published prithvi: missing", len(missing), missing[:5], "unexpected", len(unexpected), unexpected[:5])
    net = net.cuda().eval()
    names = ["BLUE", "GREEN", "RED", "NIR_NARROW", "SWIR_1", "SWIR_2"]
    means = np.array([dm.MEANS[n] for n in names], np.float32)[:, None, None]
    stds = np.array([dm.STDS[n] for n in names], np.float32)[:, None, None]
    print("published prithvi stats", means.ravel(), stds.ravel())
    bidx = [S2_BANDS.index(b) for b in ["B02", "B03", "B04", "B8A", "B11", "B12"]]

    @torch.no_grad()
    def prob(i):
        x = cache.s2[i][bidx].astype(np.float32) * 1e-4
        x = np.where(np.isfinite(x), x, 0.0)
        x = (x - means) / stds
        with torch.autocast("cuda", dtype=torch.bfloat16):
            out = net(torch.from_numpy(x)[None].cuda())
        out = out.output if hasattr(out, "output") else out
        p = out.float().softmax(1)[0, 1].cpu().numpy()
        return (p * 255).round().astype(np.uint8)
    return prob


methods = {"otsu_vh": otsu_prob, "mndwi": lambda i: index_prob(i, "B03", "B11"),
           "ndwi": lambda i: index_prob(i, "B03", "B08")}
if torch.cuda.is_available():
    methods["prithvi_published"] = published_prithvi()

for proto in ("official", "lio"):
    for name, fn in methods.items():
        out = f"{HOME}/runs/{proto}_{name}"
        os.makedirs(out, exist_ok=True)
        res = {"args": {"model": name, "protocol": proto, "mode": "none", "seed": 0}}
        for split in ("val", "test", "bolivia"):
            ids = cache.split(proto, split)
            idx = [cache.pos[c] for c in ids]
            prob = np.stack([fn(i) for i in idx])
            np.save(f"{out}/prob_{split}.npy", prob)
            labels = np.stack([cache.label[i] for i in idx])
            jrc = np.stack([cache.jrc[i] for i in idx])
            res[split] = evaluate(prob, labels, [chip_event(c) for c in ids], jrc=jrc)
            res[split]["chips"] = ids
        json.dump(res, open(f"{out}/results.json", "w"), indent=1)
        print(proto, name, "test", {k: round(v, 3) for k, v in res["test"]["pooled"].items()},
              "bolivia IoU", round(res["bolivia"]["pooled"]["iou"], 3), flush=True)
