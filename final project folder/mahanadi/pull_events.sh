#!/bin/bash
# Pull Sentinel-1 RTC + Sentinel-2 L2A + JRC for three Mahanadi-delta flood dates and a dry-season
# reference for each (Microsoft Planetary Computer, no login). Dates from the AI4G archive list
# (datakit/manifests/mahanadi_delta_flood_dates_ai4g.csv). AOI: central delta around Cuttack-Kendrapara.
H=/home1/vineet/floodfm
PY=$H/env/bin/python
S=$H/code/mahanadi/pull_s1s2.py
OUT=$H/data/mahanadi
BBOX="85.80 20.25 86.45 20.65"
mkdir -p $OUT
for pair in "2022-08-16:3:event" "2022-03-15:10:dry2022" "2021-05-29:3:event" "2021-03-10:10:dry2021" "2020-08-26:3:event" "2020-03-10:10:dry2020"; do
  IFS=: read d w tag <<< "$pair"
  echo "[$(date +%T)] $d ($tag)"
  $PY $S --bbox $BBOX --date $d --days $w --out $OUT/${tag}_${d//-/} 2>&1 | tail -4
done
echo MAHANADI_PULL_DONE
