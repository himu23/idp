#!/bin/bash
# Context layers for the other basins in mahanadi/basins.py: GloFAS discharge, ERA5 rain, land cover, elevation,
# population, soils, JRC water occurrence, building footprints and OpenStreetMap (Overpass if it answers within
# 25 minutes, the Geofabrik extract for whatever is still missing).
#   bash code/server/bg.sh logs/basins_context.log bash code/server/run_basins_context.sh [basin ...]
H=/home1/vineet/floodfm
cd $H
export PYTHONWARNINGS=ignore
PY="nice env/bin/python"
for B in ${@:-brahmani brahmaputra}; do
  C=data/${B}_context
  mkdir -p $C
  echo "== context $B $(date +%T)"
  $PY code/mahanadi/fetch_context.py --basin $B --out $C --only discharge,rain,rasters,jrc || echo "FAILED context $B"
  PBF=$(env/bin/python -c "import sys; sys.path.insert(0, 'code/mahanadi'); from basins import BASINS; print(BASINS['$B']['pbf'])")
  [ -s data/osm/$PBF-latest.osm.pbf ] || wget -q -O data/osm/$PBF-latest.osm.pbf \
      https://download.geofabrik.de/asia/india/$PBF-latest.osm.pbf || echo "FAILED download $PBF"
  timeout 1500 $PY code/mahanadi/fetch_context.py --basin $B --out $C --only osm || echo "overpass incomplete for $B"
  $PY code/mahanadi/fetch_osm_pbf.py data/osm/$PBF-latest.osm.pbf $C $B || echo "FAILED extract $B"
  $PY code/mahanadi/fetch_context.py --basin $B --out $C --only buildings || echo "FAILED buildings $B"
done
echo "BASINS_CONTEXT_DONE $(date +%T)"
