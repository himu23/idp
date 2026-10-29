#!/bin/bash
# PINN environment (Python 3.7 + TensorFlow 1.15, CPU): same pins as the repo's SETUP.sh,
# created with micromamba because the server has no conda.
set -e
P=/home1/vineet/floodfm/pinn
mkdir -p $P/mamba && cd $P/mamba
[ -x bin/micromamba ] || curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
export MAMBA_ROOT_PREFIX=$P/mamba/root
[ -x $P/env/bin/python ] || ./bin/micromamba create -y -p $P/env -c conda-forge python=3.7 pip
$P/env/bin/pip install -q tensorflow==1.15.0 numpy==1.18.5 h5py==2.10.0 scipy==1.4.1 \
    matplotlib==3.5.3 seaborn==0.11.2 pyDOE==0.3.8 protobuf==3.20.3
cd $P/PINN
CUDA_VISIBLE_DEVICES="" ../env/bin/python phase4_validation/validate.py --case 3
echo PINN_SETUP_DONE
