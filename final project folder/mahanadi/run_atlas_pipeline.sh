#!/bin/bash
# Flood atlas -> impacts -> bulletins -> field check points -> figures -> viewer -> Sentinel-2 check, on the lab server.
#   bash code/mahanadi/run_atlas_pipeline.sh <tag>   (outputs in runs/_atlas/{build,impact,figures,checkpoints}_<tag>)
#   SKIP_BUILD=1 SKIP_S2=1 bash ...   re-runs everything after the atlas build (minutes instead of ~45 min)
# Threshold 0.30 = chosen on Sen1Floods11 validation for the 20 m radar fusion (scripts/test_resolution.py).
H=/home1/vineet/floodfm
TAG=${1:-final}
PY="nice $H/env/bin/python"
export PYTHONWARNINGS=ignore ATLAS_DIR=$H/runs/_atlas/build_$TAG IMPACT_DIR=$H/runs/_atlas/impact_$TAG
cd $H/code/mahanadi
if [ -z "$SKIP_BUILD" ]; then
  echo "== build $(date +%T)"
  $PY atlas_build.py --prob $H/runs/_atlas/prob --inventory $H/data/mahanadi_atlas20/inventory.csv \
      --context $H/data/mahanadi_context --jrc $H/data/mahanadi/event_20200826/jrc_occurrence.tif \
      --out $ATLAS_DIR --model mean --thr 0.30 || { echo "FAILED build"; exit 1; }
fi
for s in impact_exposure impact_transport impact_siting impact_geotech; do
  echo "== $s $(date +%T)"
  $PY $s.py || echo "FAILED $s"
done
echo "== travel time + bulletins $(date +%T)"
$PY travel_time.py $H/data/mahanadi_context/discharge.csv $IMPACT_DIR || echo "FAILED travel_time"
for T in 5 25; do
  Q=$($PY -c "import json; print(json.load(open('$ATLAS_DIR/atlas_summary.json'))['gumbel']['return_period_m3s']['$T'])")
  $PY forecast_to_impact.py --q $Q --lead "24 h" > /dev/null || echo "FAILED bulletin T$T"
done
# 5-year flow with a dry week (20 mm) and with the monsoon 95th-percentile 7-day rain (the heavy-rain scenario)
Q5=$($PY -c "import json; print(json.load(open('$ATLAS_DIR/atlas_summary.json'))['gumbel']['return_period_m3s']['5'])")
RH=$($PY -c "import json; print(json.load(open('$ATLAS_DIR/atlas_summary.json'))['heavy_rain_scenario']['rain_mm'])")
for RAIN in 20 $RH; do
  $PY forecast_to_impact.py --q $Q5 --rain $RAIN --lead "24 h" > /dev/null || echo "FAILED bulletin rain $RAIN"
done
echo "== checkpoints $(date +%T)"
$PY make_checkpoints.py $ATLAS_DIR $IMPACT_DIR $H/runs/_atlas/checkpoints_$TAG || echo "FAILED checkpoints"
echo "== figures $(date +%T)"
$PY make_atlas_figures.py $H/runs/_atlas/figures_$TAG $H/runs/_atlas/checkpoints_$TAG || echo "FAILED figures"
echo "== dashboard $(date +%T)"
$PY make_dashboard.py $H/runs/_atlas/checkpoints_$TAG $H/runs/_atlas/dashboard_$TAG.html || echo "FAILED dashboard"
if [ -z "$SKIP_S2" ]; then
  echo "== sentinel-2 check $(date +%T)"
  $PY s2_crosscheck.py --prob $H/runs/_atlas/prob --inventory $H/data/mahanadi_atlas20/inventory.csv \
      --normal $ATLAS_DIR/normal_water_latest.tif --out $IMPACT_DIR --thr 0.30 || echo "FAILED s2"
fi
echo "PIPELINE_DONE $TAG $(date +%T)"
