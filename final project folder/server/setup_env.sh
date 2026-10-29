#!/bin/bash
# One-time setup of the training environment and Sen1Floods11 data on the lab server.
set -euo pipefail
V=/home1/vineet
P=$V/floodfm
mkdir -p $P/{data,runs,logs,code,hf}
export UV_CACHE_DIR=$V/envs/uv-cache UV_PYTHON_INSTALL_DIR=$V/envs/python UV_LINK_MODE=copy
UV=$V/envs/_uv_bootstrap/bin/uv
echo "[$(date)] create venv"
[ -x $P/env/bin/python ] || $UV venv $P/env --python 3.12
PY=$P/env/bin/python
echo "[$(date)] torch"
$UV pip install --python $PY torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128
echo "[$(date)] terratorch + tools"
$UV pip install --python $PY terratorch rasterio scikit-image pandas pyarrow matplotlib huggingface_hub tensorboard pyyaml scikit-learn
$PY -c "import torch,terratorch;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),'terratorch',terratorch.__version__)"
echo "[$(date)] Sen1Floods11 v1.1"
cd $P/data
if [ ! -d sen1floods11_v1.1 ]; then
  HF_HOME=$P/hf $P/env/bin/hf download blumenstiel/Sen1Floods11 sen1floods11_v1_1.tar.gz --repo-type dataset --local-dir ./
  tar -xzf sen1floods11_v1_1.tar.gz && rm -f sen1floods11_v1_1.tar.gz
fi
ls sen1floods11_v1.1 sen1floods11_v1.1/*
echo "[$(date)] SETUP_DONE"
