#!/bin/bash
# Download Sen1Floods11 v1.1 (hand-labelled part, 1.77 GB) from the Hugging Face copy and unpack it.
cd /home1/vineet/floodfm/data
rm -rf .cache
URL=https://huggingface.co/datasets/blumenstiel/Sen1Floods11/resolve/main/sen1floods11_v1_1.tar.gz
for i in $(seq 1 20); do
  wget -c -q --timeout=60 --tries=3 "$URL" && break
  echo "retry $i $(ls -la sen1floods11_v1_1.tar.gz)"; sleep 5
done
ls -la sen1floods11_v1_1.tar.gz
sha256sum sen1floods11_v1_1.tar.gz   # expected d836b0c9...640a4f (datakit README)
tar -xzf sen1floods11_v1_1.tar.gz && rm sen1floods11_v1_1.tar.gz && echo DATA_DONE
