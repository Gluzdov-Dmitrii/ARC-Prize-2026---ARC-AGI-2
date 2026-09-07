#!/bin/bash
set -euo pipefail
PROJECT=/home/scientists/gluz_d_s/kaggle/projects/arc-prize-2026-arc-agi-2
ENV=$PROJECT/envs/ngpu01/py3.11-cu124-unsloth-wip
export PIP_CACHE_DIR=$PROJECT/cache/pip
export TMPDIR=$PROJECT/cache/tmp
export HF_HUB_CACHE=$PROJECT/cache/hf
export TRANSFORMERS_CACHE=$PROJECT/cache/hf
export TORCH_HOME=$PROJECT/cache/torch
export XDG_CACHE_HOME=$PROJECT/cache/xdg
mkdir -p "$PIP_CACHE_DIR" "$TMPDIR" "$HF_HUB_CACHE" "$TORCH_HOME" "$XDG_CACHE_HOME"
PY=$ENV/bin/python
$PY -m pip install --upgrade pip
$PY -m pip install torch --index-url https://download.pytorch.org/whl/cu124
# Install the Kaggle-pinned stack except Unsloth extras that pull CUDA 13 wheels.
$PY -m pip install -r $PROJECT/code/m0-portable-v1/configs/requirements-m0.txt
$PY -m pip install --no-deps unsloth==2025.9.7 unsloth-zoo==2025.9.9
# Restore driver-matched torch; drop wheels that require torch 2.14/CUDA 13.
$PY -m pip uninstall -y xformers torchvision torchao || true
$PY -m pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu124
$PY -m pip install fsspec==2025.3.0
$PY -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.version.cuda)"
$PY -m pip freeze > $ENV/pip-freeze.txt
echo INSTALL_DONE
