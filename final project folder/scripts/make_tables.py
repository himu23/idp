"""Turn results/analysis/summary.json into the Markdown result tables of the final report.

    python scripts/make_tables.py results/analysis report/sections/02_tables.md
"""
import json
import sys

src, dst = sys.argv[1], sys.argv[2]
S = json.load(open(f"{src}/summary.json"))
PE = json.load(open(f"{src}/per_event_official.json"))
TH = json.load(open(f"{src}/thresholds.json"))
ORDER = ["otsu_vh", "mndwi", "ndwi", "prithvi_published", "cnn", "unet", "prithvi", "terramind", "dofa", "clay",
         "satlas", "decur", "ens_mean", "ens_weighted", "ens_learned", "ensall_mean", "ensall_learned", "enstop3_mean"]
FMS = ["prithvi", "terramind", "dofa", "clay", "satlas", "decur"]


def get(proto, model, mode=None, mods="default"):
    for s in S:
        if s["protocol"] == proto and s["model"] == model and s["modalities"] == mods and (mode is None or s["mode"] == mode):
            return s
    return None


def pm(s, k, d=3):
    if s is None:
        return "–"
    v, sd = s[k], s.get(k + "_std", 0)
    return f"{v:.{d}f} ± {sd:.{d}f}" if s["n_seeds"] > 1 else f"{v:.{d}f}"


out = []
for proto, title in (("lio", "Table A. Unseen Indian flood (leave-India-out; test = 68 Assam chips)"),
                     ("official", "Table B. Official Sen1Floods11 split (test = 90 chips, 10 events)")):
    out.append(f"**{title}.** Water IoU and companions on test; mean ± sd over seeds where n > 1. "
               "Calibrated = threshold chosen on validation. Non-perm. = IoU on pixels that are not JRC permanent water. "
               "Bolivia = official hold-out event (never trained on).\n")
    out.append("| Method | Group | n | Test IoU | F1 | Precision | Recall | Calibrated IoU (thr) | Non-perm. IoU | Bolivia IoU | Params (M) | Train (min) |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    rows = [s for s in S if s["protocol"] == proto and s["modalities"] == "default" and s["mode"] in ("full", "none")
            and s["model"] in ORDER]
    rows.sort(key=lambda s: ORDER.index(s["model"]))
    for s in rows:
        out.append(f"| {s['label']} | {s['group']} | {s['n_seeds']} | **{pm(s, 'test_iou')}** | {pm(s, 'test_f1')} | "
                   f"{pm(s, 'test_precision')} | {pm(s, 'test_recall')} | {s['test_iou_calibrated']:.3f} ({s['threshold']:.2f}) | "
                   f"{pm(s, 'test_nonpermanent_iou')} | {pm(s, 'bolivia_iou')} | "
                   f"{s['params_M'] if s['params_M'] else '–'} | {s['train_min'] if s['train_min'] else '–'} |")
    out.append("")

out.append("**Table C. Frozen encoder vs full fine-tuning** (test water IoU; frozen = seed 0, fine-tuned = mean of seeds).\n")
out.append("| Model | LIO frozen | LIO fine-tuned | Δ | Official frozen | Official fine-tuned | Δ | Trainable params frozen (M) |")
out.append("|---|---|---|---|---|---|---|---|")
for m in FMS:
    lf, lu, of, ou = get("lio", m, "frozen"), get("lio", m, "full"), get("official", m, "frozen"), get("official", m, "full")
    if not (lf and lu and of and ou):
        continue
    out.append(f"| {lu['label']} | {lf['test_iou']:.3f} | {lu['test_iou']:.3f} | {lu['test_iou'] - lf['test_iou']:+.3f} | "
               f"{of['test_iou']:.3f} | {ou['test_iou']:.3f} | {ou['test_iou'] - of['test_iou']:+.3f} | {lf['trainable_M']} |")
out.append("")

out.append("**Table D. Which sensor is needed? Modality ablation on the unseen Indian flood** (LIO test IoU, mean ± sd over seeds).\n")
out.append("| Model | Radar only (S1) | Optical only (S2) | Radar + optical |")
out.append("|---|---|---|---|")
for m in ("unet", "terramind"):
    a, b, c = get("lio", m, "full", "s1"), get("lio", m, "full", "s2"), get("lio", m, "full")
    if a or b:
        out.append(f"| {(c or a or b)['label']} | {pm(a, 'test_iou')} | {pm(b, 'test_iou')} | {pm(c, 'test_iou')} |")
out.append("")

out.append("**Table E. Fusion of the six fine-tuned foundation models** (test IoU, mean ± sd over seeds; best single model for reference).\n")
out.append("| Variant | LIO (Assam) | Official | Bolivia (LIO models) |")
out.append("|---|---|---|---|")
for proto_best in ("lio",):
    pass
best_l = max([get("lio", m, "full") for m in FMS if get("lio", m, "full")], key=lambda s: s["val_iou"], default=None)
best_o = max([get("official", m, "full") for m in FMS if get("official", m, "full")], key=lambda s: s["val_iou"], default=None)
if best_l and best_o:
    out.append(f"| Best single FM by validation ({best_l['label']} / {best_o['label']}) | {pm(best_l, 'test_iou')} | "
               f"{pm(best_o, 'test_iou')} | {pm(best_l, 'bolivia_iou')} |")
for k in ("ens_mean", "ens_weighted", "ens_learned", "ensall_mean", "ensall_learned", "enstop3_mean"):
    a, b = get("lio", k), get("official", k)
    if a or b:
        out.append(f"| {(a or b)['label']} | {pm(a, 'test_iou')} | {pm(b, 'test_iou')} | {pm(a, 'bolivia_iou')} |")
coef = {n: v["coef"] for n, v in TH.items() if (n.endswith("ens_learned_s0") or n.endswith("ensall_learned_s0")) and v.get("coef")}
if coef:
    out.append("")
    for n, c in coef.items():
        out.append(f"Learned fuse-layer weights ({n.rsplit('_', 2)[0]}, seed 0): " +
                   ", ".join(f"{k} {v:+.2f}" for k, v in c.items()) + ".")
out.append("")

events = sorted({e for d in PE.values() for e in d})
out.append("**Table F. Per-event test IoU, official split** (mean over seeds; fine-tuned models and baselines).\n")
models = [m for m in ORDER if m in PE]
out.append("| Event | " + " | ".join(next(s['label'] for s in S if s['model'] == m) for m in models) + " |")
out.append("|---|" + "---|" * len(models))
for e in events:
    out.append(f"| {e} | " + " | ".join(f"{PE[m].get(e, float('nan')):.2f}" for m in models) + " |")
out.append("")
try:
    LE = json.load(open(f"{src}/label_efficiency.json"))
    out.append("**Table G. Label efficiency on the unseen Indian flood** (LIO test IoU, mean ± sd over seeds; nested "
               "subsets of the 212 non-Indian training chips; epochs scaled so every run gets ~1,000 updates).\n")
    out.append("| Model | 21 chips (10 %) | 53 chips (25 %) | 106 chips (50 %) | 212 chips (100 %) |")
    out.append("|---|---|---|---|---|")
    for m, d in LE.items():
        lab = next(s["label"] for s in S if s["model"] == m)
        out.append(f"| {lab} | " + " | ".join(f"{d[k][0]:.3f} ± {d[k][1]:.3f}" if k in d else "–"
                                               for k in ("10", "25", "50", "100")) + " |")
    out.append("")
except FileNotFoundError:
    pass
open(dst, "w", encoding="utf-8").write("\n".join(out))
print("written", dst, len(out), "lines")
