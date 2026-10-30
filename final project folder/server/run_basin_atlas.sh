#!/bin/bash
# Flood atlas, trigger map, design floods, exposure and the flow-impact tables for one of the other basins
# (mahanadi/basins.py), with the production radar pair (TerraMind-B + U-Net retrained on 20 m input, threshold 0.45).
#   bash code/server/bg.sh logs/<basin>_atlas.log bash code/server/run_basin_atlas.sh <basin> [--wait]
# --wait maps passes while the pull is still running (logs/<basin>_atlas20_pull.log must say ATLAS_PULL_DONE at the end).
H=/home1/vineet/floodfm
B=$1
cd $H
export PYTHONWARNINGS=ignore
PY="nice $H/env/bin/python"
P=$H/runs/_atlas/prob_$B
echo "== infer $B $(date +%T)"
CUDA_VISIBLE_DEVICES=0 $PY code/mahanadi/atlas_infer.py code data/${B}_atlas20 --out $P $2 \
    --runs runs/official_terramind_s1_full_s0_r20 > logs/${B}_infer_terramind.log 2>&1 &
CUDA_VISIBLE_DEVICES=1 $PY code/mahanadi/atlas_infer.py code data/${B}_atlas20 --out $P $2 \
    --runs runs/official_unet_s1_full_s0_r20 > logs/${B}_infer_unet.log 2>&1 &
wait
echo "maps: $(ls $P | wc -l)"
read GAUGE DRY WET <<< $(env/bin/python -c "import sys; sys.path.insert(0, 'code/mahanadi'); from basins import BASINS; b = BASINS['$B']; print(b['gauge'], ','.join(map(str, b['dry'])), ','.join(map(str, b['wet'])))")
export ATLAS_DIR=$H/runs/_atlas/build_$B IMPACT_DIR=$H/runs/_atlas/impact_$B CONTEXT_DIR=$H/data/${B}_context
mkdir -p $IMPACT_DIR
cd $H/code/mahanadi
echo "== build $B gauge $GAUGE dry $DRY wet $WET $(date +%T)"
$PY atlas_build.py --prob $P --inventory $H/data/${B}_atlas20/inventory.csv --context $CONTEXT_DIR \
    --jrc $CONTEXT_DIR/jrc_occurrence.tif --out $ATLAS_DIR --model mean --thr 0.45 --gauge $GAUGE --dry $DRY --wet $WET \
    || { echo "FAILED build"; exit 1; }
for s in impact_exposure impact_curve; do
  echo "== $s $(date +%T)"
  $PY $s.py || echo "FAILED $s"
done
echo "== sentinel-2 check $(date +%T)"
$PY s2_crosscheck.py --prob $P --inventory $H/data/${B}_atlas20/inventory.csv --normal $ATLAS_DIR/normal_water_latest.tif \
    --out $IMPACT_DIR --thr 0.45 --basin $B || echo "FAILED s2"
echo "BASIN_ATLAS_DONE $B $(date +%T)"
