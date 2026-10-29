"""One scoring routine for every method (thresholds, CNNs, foundation models, ensembles).

Water class only, over labelled pixels (label >= 0). Counts are pooled over all
chips of a split (the convention of the mentor notebook and the Prithvi paper);
mean per-chip IoU and per-event scores are reported alongside.
"""
import numpy as np


def counts(pred, label, mask=None):
    """pred: bool water map, label: int {-1,0,1}. Returns tp, fp, fn, tn over valid pixels."""
    valid = label >= 0
    if mask is not None:
        valid &= mask
    t = (label == 1) & valid
    p = pred & valid
    tp = int((t & p).sum())
    fp = int((~t & p).sum())
    fn = int((t & ~p).sum())
    tn = int((valid & ~t & ~p).sum())
    return tp, fp, fn, tn


def scores(tp, fp, fn, tn=0):
    iou = tp / max(tp + fp + fn, 1)
    f1 = 2 * tp / max(2 * tp + fp + fn, 1)
    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    acc = (tp + tn) / max(tp + fp + fn + tn, 1)
    return {"iou": iou, "f1": f1, "precision": prec, "recall": rec, "accuracy": acc}


def evaluate(prob, labels, events, thr=0.5, jrc=None):
    """prob: [N,H,W] water probability (float or uint8/255), labels: [N,H,W], events: list of N names.

    Returns pooled scores, mean per-chip IoU (chips that contain water), per-event pooled
    scores and -- if jrc is given -- scores restricted to pixels that are NOT permanent
    water, i.e. how well the model finds flood water rather than rivers and lakes.
    """
    if prob.dtype == np.uint8:
        thr_u8 = int(round(thr * 255))
        predict = lambda a: a >= thr_u8  # noqa: E731
    else:
        predict = lambda a: a >= thr  # noqa: E731
    total = np.zeros(4, np.int64)
    flood_total = np.zeros(4, np.int64)
    per_event, chip_iou = {}, []
    for i in range(len(prob)):
        p = predict(prob[i])
        c = np.array(counts(p, labels[i]))
        total += c
        per_event.setdefault(events[i], np.zeros(4, np.int64))
        per_event[events[i]] += c
        if (labels[i] == 1).any():
            chip_iou.append(scores(*c)["iou"])
        if jrc is not None:
            flood_total += np.array(counts(p, labels[i], mask=jrc[i] == 0))
    out = {"pooled": scores(*total), "counts": total.tolist(),
           "mean_chip_iou": float(np.mean(chip_iou)) if chip_iou else float("nan"),
           "per_event": {e: scores(*c) for e, c in sorted(per_event.items())}}
    if jrc is not None:
        out["non_permanent"] = scores(*flood_total)
    return out


def threshold_sweep(prob, labels, thresholds=None):
    """Pooled IoU/F1/precision/recall at each threshold (used on validation to pick one)."""
    if thresholds is None:
        thresholds = np.round(np.arange(0.1, 0.91, 0.05), 2)
    valid = labels >= 0
    truth = (labels == 1) & valid
    p = prob.astype(np.float32) / (255.0 if prob.dtype == np.uint8 else 1.0)
    rows = []
    for t in thresholds:
        pr = (p >= t) & valid
        tp = int((pr & truth).sum()); fp = int((pr & ~truth).sum()); fn = int((~pr & truth).sum())
        rows.append({"threshold": float(t), **scores(tp, fp, fn)})
    return rows
