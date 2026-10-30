"""Compare the atlas built with the 10 m-trained radar pair (archived) with the rebuilt one (20 m-trained pair).

Reads the archived results in results/archive_atlas_10m/ and the current ones in results/atlas and results/impact, and
writes results/archive_atlas_10m/compare.json, the table of report Appendix B.

    python scripts/compare_atlases.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
ARC = os.path.join(RES, "archive_atlas_10m")


def J(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return json.load(f)


def row(atlas, s2):
    v = atlas["validation"]
    a, f = s2["all/all_months"], s2["outside_normal/all_months"]
    hf, sett = v["high_flow_passes"], v["settlements"]["high_flow_passes"]["model"]
    return dict(threshold=atlas["threshold"], s2_pairs=s2["pairs"],
                s2_all_iou=a["iou"], s2_all_precision=a["precision"], s2_all_recall=a["recall"],
                s2_flood_iou=f["iou"], s2_flood_precision=f["precision"], s2_flood_recall=f["recall"],
                hf_iou=hf["model"]["iou"], hf_clim_iou=hf["climatology"]["iou"], hf_passes=hf["n"],
                all_iou=v["all_monsoon_passes"]["model"]["iou"], all_clim_iou=v["all_monsoon_passes"]["climatology"]["iou"],
                sett_hf_pod=sett["POD"], sett_hf_far=sett["FAR"], sett_hf_csi=sett["CSI"],
                ever_km2=atlas["flooded_ever_km2"], river_driven_km2=atlas["river_driven_km2"],
                rain_spearman=atlas["rain_spearman"][atlas["rain_predictor"]], rain_predictor=atlas["rain_predictor"],
                predictor=atlas["predictor"])


out = dict(old=row(J(ARC, "atlas_summary.json"), J(ARC, "s2_crosscheck.json")),
           new=row(J(RES, "atlas", "atlas_summary.json"), J(RES, "impact", "s2_crosscheck.json")),
           note="old: radar TerraMind-B + U-Net trained on 10 m Sentinel-1; new: the same pair retrained on 20 m input "
                "(floodfm/train.py --s1_res 20). Sentinel-2 scores use the same optical reference for both; held-out "
                "scores are each atlas against its own observed maps.")
with open(os.path.join(ARC, "compare.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
print(json.dumps(out, indent=1))
