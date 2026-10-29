#!/usr/bin/env bash
# Download Sen1Floods11 — the SAME data Siddik's Flood_AI.ipynb uses — plus the extra India chips.
# Usage:  bash 01_download_sen1floods11.sh <data_root>        (e.g. bash 01_download_sen1floods11.sh ~/idp_data)
#   Step A (always):  hand-labelled package, 446 chips, 1.77 GB, from Hugging Face (identical to the notebook)
#   Step B (default): India weakly-labelled chips, 467 chips x 4 files (~3.5 GB) from the original public GCS bucket
#   Set ALL_WEAK=1 to also fetch weak labels for all countries (4,384 chips, ~33 GB).
set -euo pipefail
ROOT=${1:-./idp_data}; mkdir -p "$ROOT/sen1floods11" && cd "$ROOT/sen1floods11"

echo "== A. hand-labelled Sen1Floods11 v1.1 (Hugging Face mirror by IBM's B. Blumenstiel of cloudtostreet/Sen1Floods11)"
if [ ! -d sen1floods11_v1.1 ]; then
  curl -L -C - --retry 5 -o sen1floods11_v1_1.tar.gz \
    https://huggingface.co/datasets/blumenstiel/Sen1Floods11/resolve/main/sen1floods11_v1_1.tar.gz
  echo "d836b0c9772f2bbbe1d96912a5fc8b4eb4752309ee864b320cff78fc4f640a4f  sen1floods11_v1_1.tar.gz" | sha256sum -c -
  tar -xzf sen1floods11_v1_1.tar.gz && rm sen1floods11_v1_1.tar.gz
fi
B=https://storage.googleapis.com/sen1floods11/v1.1
curl -sS -O $B/Sen1Floods11_Metadata.geojson      # event dates, orbits, footprints
curl -sS -O $B/catalog.zip                         # STAC catalogue: per-chip footprint + date

echo "== B. weakly-labelled chips from the original bucket gs://sen1floods11 (no login needed)"
PAT='India_'; [ "${ALL_WEAK:-0}" = "1" ] && PAT=''
mkdir -p weak && cd weak
python3 - "$PAT" <<'PY'
import json, sys, urllib.request, urllib.parse
pat = sys.argv[1]; tok = None; urls = []
while True:
    q = {'prefix': 'v1.1/data/flood_events/WeaklyLabeled/', 'maxResults': 1000, 'fields': 'items(name),nextPageToken'}
    if tok: q['pageToken'] = tok
    d = json.load(urllib.request.urlopen('https://storage.googleapis.com/storage/v1/b/sen1floods11/o?' + urllib.parse.urlencode(q)))
    urls += ['https://storage.googleapis.com/sen1floods11/' + i['name'] for i in d.get('items', []) if i['name'].endswith('.tif') and pat in i['name'].split('/')[-1]]
    tok = d.get('nextPageToken')
    if not tok: break
open('urls.txt', 'w').write('\n'.join(urls) + '\n'); print(len(urls), 'files to fetch')
PY
# keeps the bucket folder layout: S1Weak/, S2Weak/, S1OtsuLabelWeak/, S2IndexLabelWeak/
xargs -P 8 -n 1 sh -c 'p=${0#https://storage.googleapis.com/sen1floods11/v1.1/data/flood_events/WeaklyLabeled/}; mkdir -p "$(dirname "$p")"; [ -s "$p" ] || curl -sS --retry 3 -o "$p" "$0"' < urls.txt
echo "done -> $ROOT/sen1floods11"
