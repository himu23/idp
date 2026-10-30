#!/bin/bash
# Radar archives of the other basins in mahanadi/basins.py, one after the other (Planetary Computer throttles
# parallel pulls from this server). Same period and 20 m overviews as the Mahanadi atlas.
#   bash code/server/bg.sh logs/basins_pull.log bash code/server/run_basins_pull.sh [basin ...]
H=/home1/vineet/floodfm
cd $H
export PYTHONWARNINGS=ignore
for B in ${@:-brahmani brahmaputra}; do
  M=$(env/bin/python -c "import sys; sys.path.insert(0, 'code/mahanadi'); from basins import BASINS; b = BASINS['$B']; print(','.join(map(str, sorted(b['dry'] + b['wet']))))")
  echo "== pull $B months $M $(date +%T)"
  nice env/bin/python code/mahanadi/atlas_pull.py --basin $B --out data/${B}_atlas20 --res 20 --months $M \
      || echo "FAILED pull $B"
  echo "passes: $(ls data/${B}_atlas20/*.tif 2>/dev/null | wc -l)"
done
echo "PULLS_DONE $(date +%T)"
