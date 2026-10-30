#!/bin/bash
# Candidate atlas with the radar pair retrained on 20 m input (report Appendix B), built beside the current one.
# Maps every pass with both models in parallel (one GPU each), builds the atlas at the threshold chosen on validation
# for this pair (0.45) and runs the Sentinel-2 check, so the two atlases can be compared before anything is replaced.
#   bash code/server/bg.sh logs/r20_candidate.log bash code/server/run_r20_candidate.sh
H=/home1/vineet/floodfm
cd $H
export PYTHONWARNINGS=ignore
PY="nice $H/env/bin/python"
echo "== infer $(date +%T)"
CUDA_VISIBLE_DEVICES=0 $PY code/mahanadi/atlas_infer.py code data/mahanadi_atlas20 --out runs/_atlas/prob_r20 \
    --runs runs/official_terramind_s1_full_s0_r20 > logs/r20_infer_terramind.log 2>&1 &
CUDA_VISIBLE_DEVICES=1 $PY code/mahanadi/atlas_infer.py code data/mahanadi_atlas20 --out runs/_atlas/prob_r20 \
    --runs runs/official_unet_s1_full_s0_r20 > logs/r20_infer_unet.log 2>&1 &
wait
echo "maps: $(ls runs/_atlas/prob_r20 | wc -l)"
export ATLAS_DIR=$H/runs/_atlas/build_r20 IMPACT_DIR=$H/runs/_atlas/impact_r20
mkdir -p $IMPACT_DIR
cd $H/code/mahanadi
echo "== build $(date +%T)"
$PY atlas_build.py --prob $H/runs/_atlas/prob_r20 --inventory $H/data/mahanadi_atlas20/inventory.csv \
    --context $H/data/mahanadi_context --jrc $H/data/mahanadi/event_20200826/jrc_occurrence.tif \
    --out $ATLAS_DIR --model mean --thr 0.45 || { echo "FAILED build"; exit 1; }
echo "== sentinel-2 check $(date +%T)"
$PY s2_crosscheck.py --prob $H/runs/_atlas/prob_r20 --inventory $H/data/mahanadi_atlas20/inventory.csv \
    --normal $ATLAS_DIR/normal_water_latest.tif --out $IMPACT_DIR --thr 0.45 || echo "FAILED s2"
echo "R20_CANDIDATE_DONE $(date +%T)"
