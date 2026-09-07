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
$PY -m pip install -r $PROJECT/code/m0-portable-v1/configs/requirements-m0.txt
$PY -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.version.cuda)"
$PY -m pip freeze > $PROJECT/envs/ngpu01/py3.11-cu124-unsloth-wip/pip-freeze.txt
echo INSTALL_DONE
