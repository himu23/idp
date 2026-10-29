#!/usr/bin/env bash
# Download the 4 Indian scenes (Cyclone Fani, Odisha, May 2019; includes Cuttack / Mahanadi delta) from WorldFloods v2.
# ~120 MB. Licence CC BY-NC 4.0 (non-commercial / research use).  Usage: bash 05_download_worldfloods_india.sh <data_root>
set -euo pipefail
ROOT=${1:-./idp_data}; OUT="$ROOT/worldfloods_v2_india"; mkdir -p "$OUT"; cd "$OUT"
H=https://huggingface.co/datasets/isp-uv-es/WorldFloodsv2/resolve/main/train
for a in AOI03_FEP AOI05_GRA AOI06_GRA AOI08_GRA; do
  for d in S2 gt PERMANENTWATERJRC meta floodmaps; do
    ext=tif; [ $d = meta ] && ext=json; [ $d = floodmaps ] && ext=geojson
    mkdir -p $d; curl -sS -L -o $d/EMSR357_${a}_PRODUCT.$ext $H/$d/EMSR357_${a}_PRODUCT.$ext
  done
done
echo "gt band 1 = cloud (0 invalid, 1 clear, 2 cloud); gt band 2 = water (0 invalid, 1 land, 2 water)"
