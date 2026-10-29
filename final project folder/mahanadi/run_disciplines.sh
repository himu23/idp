#!/bin/bash
# Second stage after run_atlas_pipeline.sh: depth, structures, ground saturation, ocean drivers, construction plan,
# their figures, and the transport re-run (evacuation + delay metrics).
#   bash code/mahanadi/run_disciplines.sh <tag>
H=/home1/vineet/floodfm
TAG=${1:-final}
PY="nice $H/env/bin/python"
C=$H/data/mahanadi_context
export PYTHONWARNINGS=ignore ATLAS_DIR=$H/runs/_atlas/build_$TAG IMPACT_DIR=$H/runs/_atlas/impact_$TAG
cd $H/code/mahanadi
for s in impact_depth impact_structures impact_ground; do
  echo "== $s $(date +%T)"
  $PY $s.py || echo "FAILED $s"
done
echo "== ocean $(date +%T)"
$PY ocean_cyclones.py $C/ibtracs_NI.csv $C/rain.csv $C/discharge.csv || echo "FAILED ocean"
echo "== construction $(date +%T)"
$PY cm_plan.py $C/discharge.csv $C/ibtracs_NI.csv $H/runs/_atlas/figures_$TAG || echo "FAILED cm_plan"
echo "== checkpoints (with well-level points) $(date +%T)"
$PY make_checkpoints.py $ATLAS_DIR $IMPACT_DIR $H/runs/_atlas/checkpoints_$TAG || echo "FAILED checkpoints"
echo "== figures $(date +%T)"
$PY make_discipline_figures.py $H/runs/_atlas/figures_$TAG $H/runs/_atlas/checkpoints_$TAG || echo "FAILED discipline figures"
echo "== dashboard $(date +%T)"
$PY make_dashboard.py $H/runs/_atlas/checkpoints_$TAG $H/runs/_atlas/dashboard_$TAG.html || echo "FAILED dashboard"
echo "DISCIPLINES_DONE $TAG $(date +%T)"
