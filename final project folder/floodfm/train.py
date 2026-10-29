"""Train one model under one protocol and score it. Same recipe for every model.

    python -m floodfm.train --model terramind --protocol lio --mode full --seed 0 --out runs/...

Recipe (identical for all models, only the learning rates differ between
from-scratch and pre-trained encoders):
  * input: full 512x512 chips, random D4 augmentation (rotations + flips, applied on the GPU)
  * loss: cross-entropy + soft Dice on the water class, unknown pixels (-1) ignored
  * AdamW, 2-epoch linear warm-up then cosine decay, bf16 autocast
  * model selection: epoch with the best validation water IoU (threshold 0.5)
  * test chips are touched exactly once, after training, with the selected weights
Outputs in --out: results.json, water probabilities (uint8, 0-255) for val/test/bolivia,
and optionally the selected weights.
"""
import argparse
import copy
import json
import os
import time

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from .data import Cache, FloodChips, Normalizer, chip_event, gpu_d4
from .metrics import evaluate
from .models import SPECS, build, model_stats


def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, choices=list(SPECS))
    p.add_argument("--protocol", default="official", choices=["official", "lio"])
    p.add_argument("--mode", default="full", choices=["full", "frozen"])
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--bs", type=int, default=8)
    p.add_argument("--lr_backbone", type=float, default=5e-5)
    p.add_argument("--lr_head", type=float, default=3e-4)
    p.add_argument("--lr_scratch", type=float, default=1e-3)
    p.add_argument("--modalities", default="", help="ablation: 's1', 's2' or 's1s2' (default: model spec)")
    # the cache is copied to RAM (/dev/shm) on the server: the data disks are 7200 rpm HDDs
    p.add_argument("--cache", default="/dev/shm/floodfm_cache" if os.path.isdir("/dev/shm/floodfm_cache")
                   else "/home1/vineet/floodfm/data/cache")
    p.add_argument("--out", required=True)
    p.add_argument("--save_ckpt", action="store_true")
    p.add_argument("--train_frac", type=float, default=1.0,
                   help="label-efficiency runs: use a nested random subset of the training chips; epochs are "
                        "scaled by 1/frac so every run gets about the same number of optimiser updates")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--s1_res", type=int, default=10, choices=[10, 20],
                   help="20: train and select on radar degraded to the 20 m overview the Mahanadi atlas reads")
    return p.parse_args()


def dice_loss(logits, y):
    valid = (y >= 0).float()
    p = logits.float().softmax(1)[:, 1] * valid
    t = (y == 1).float() * valid
    inter = (p * t).sum()
    return 1 - (2 * inter + 1) / (p.sum() + t.sum() + 1)


def to_dev(x, norm):
    return norm({k: v.cuda(non_blocking=True) for k, v in x.items()})


@torch.no_grad()
def predict(model, loader, norm):
    """Water probability for every chip of a loader, as uint8 0..255 in loader order."""
    model.eval()
    out = []
    for x, _, _ in loader:
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(to_dev(x, norm))
        prob = logits.float().softmax(1)[:, 1]
        out.append((prob * 255).round().byte().cpu().numpy())
    return np.concatenate(out)


def main():
    a = parse()
    os.makedirs(a.out, exist_ok=True)
    torch.manual_seed(a.seed)
    np.random.seed(a.seed)
    cache = Cache(a.cache)
    spec = SPECS[a.model]
    use_s1, s2 = spec["s1"], spec["s2"]
    if a.modalities:
        use_s1 = "s1" in a.modalities
        s2 = spec["s2"] if "s2" in a.modalities else []
    ids = {s: cache.split(a.protocol, s) for s in ("train", "val", "test", "bolivia")}
    val_every = 1
    if a.train_frac < 1:
        perm = np.random.default_rng(1234).permutation(len(ids["train"]))   # fixed order -> nested subsets
        k = max(a.bs, int(round(a.train_frac * len(ids["train"]))))
        ids["train"] = [ids["train"][i] for i in sorted(perm[:k])]
        a.epochs = int(round(a.epochs / a.train_frac))
        val_every = int(round(1 / a.train_frac))

    stats_file = os.path.join(a.cache, f"stats_{a.protocol}.json")
    if not os.path.exists(stats_file):
        m, s = cache.channel_stats(ids["train"])
        json.dump({"mean": m, "std": s}, open(stats_file, "w"))
    st = json.load(open(stats_file))
    mean, std = model_stats(a.model, st["mean"], st["std"])

    def ds(split, aug=False):
        return FloodChips(cache, ids[split], s2, use_s1, mean, std, augment=aug)

    g = torch.Generator().manual_seed(a.seed)
    aug_gen = torch.Generator().manual_seed(a.seed + 1)
    train_dl = DataLoader(ds("train"), batch_size=a.bs, shuffle=True, drop_last=True,
                          num_workers=a.workers, generator=g, persistent_workers=True, pin_memory=True)
    eval_dl = {s: DataLoader(ds(s), batch_size=a.bs, num_workers=a.workers) for s in ("val", "test", "bolivia")}

    norm = Normalizer(train_dl.dataset, s1_res=a.s1_res).cuda()
    model = build(a.model, s1=use_s1, s2=s2).cuda()
    enc = set(id(p) for p in model.backbone_parameters())
    scratch = a.model in ("cnn", "unet")
    if a.mode == "frozen":
        for p in model.backbone_parameters():
            p.requires_grad = False
    groups = []
    if scratch:
        groups.append({"params": [p for p in model.parameters()], "lr": a.lr_scratch, "weight_decay": 1e-4})
    else:
        head = [p for p in model.parameters() if id(p) not in enc]
        groups.append({"params": head, "lr": a.lr_head, "weight_decay": 0.05})
        if a.mode == "full":
            groups.append({"params": [p for p in model.parameters() if id(p) in enc],
                           "lr": a.lr_backbone, "weight_decay": 0.05})
    opt = torch.optim.AdamW(groups)
    base_lrs = [gr["lr"] for gr in opt.param_groups]
    steps_per_epoch = len(train_dl)
    total = a.epochs * steps_per_epoch
    warm = max(1, round(0.05 * total))   # = 2 epochs for the standard 40-epoch run
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_all = sum(p.numel() for p in model.parameters())

    val_labels = np.stack([cache.label[cache.pos[c]] for c in ids["val"]])
    val_events = [chip_event(c) for c in ids["val"]]
    best, best_iou, history, step = None, -1.0, [], 0
    t0 = time.time()
    for ep in range(a.epochs):
        model.train()
        if a.mode == "frozen" and hasattr(model.net, "encoder"):
            model.net.encoder.eval()  # keep frozen BatchNorm statistics fixed
        run_loss = 0.0
        for x, y, _ in train_dl:
            frac = step / warm if step < warm else 0.5 * (1 + np.cos(np.pi * (step - warm) / max(total - warm, 1)))
            for gr, lr in zip(opt.param_groups, base_lrs):
                gr["lr"] = lr * frac
            x, y = to_dev(x, norm), y.cuda(non_blocking=True).long()
            x, y = gpu_d4(x, y, aug_gen)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                logits = model(x)
            logits = logits.float()
            loss = F.cross_entropy(logits, y, ignore_index=-1) + dice_loss(logits, y)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            run_loss += loss.item()
            step += 1
        if (ep + 1) % val_every and ep != a.epochs - 1:
            continue
        vprob = predict(model, eval_dl["val"], norm)
        v = evaluate(vprob, val_labels, val_events)["pooled"]
        history.append({"epoch": ep + 1, "loss": run_loss / steps_per_epoch, "val_iou": v["iou"],
                        "time_s": round(time.time() - t0, 1)})
        print(json.dumps(history[-1]), flush=True)
        if v["iou"] > best_iou:
            best_iou = v["iou"]
            best = {k: t.detach().cpu().clone() for k, t in model.state_dict().items()}
            best_epoch = ep + 1
    train_time = time.time() - t0
    model.load_state_dict(best)

    res = {"args": vars(a), "modalities": {"s2": list(s2), "s1": use_s1}, "params_total": n_all,
           "params_trainable": n_train, "n_train_chips": len(ids["train"]), "optimizer_steps": total,
           "best_epoch": best_epoch, "best_val_iou": best_iou,
           "train_time_s": round(train_time, 1), "history": history}
    for split in ("val", "test", "bolivia"):
        t1 = time.time()
        prob = predict(model, eval_dl[split], norm)
        res[f"infer_s_per_chip_{split}"] = (time.time() - t1) / max(len(prob), 1)
        np.save(os.path.join(a.out, f"prob_{split}.npy"), prob)
        labels = np.stack([cache.label[cache.pos[c]] for c in ids[split]])
        jrc = np.stack([cache.jrc[cache.pos[c]] for c in ids[split]])
        res[split] = evaluate(prob, labels, [chip_event(c) for c in ids[split]], jrc=jrc)
        res[split]["chips"] = ids[split]
    if a.save_ckpt:
        torch.save(best, os.path.join(a.out, "best.pt"))
    json.dump(res, open(os.path.join(a.out, "results.json"), "w"), indent=1)
    print("TEST", json.dumps(res["test"]["pooled"]), "BOLIVIA", json.dumps(res["bolivia"]["pooled"]), flush=True)


if __name__ == "__main__":
    main()
