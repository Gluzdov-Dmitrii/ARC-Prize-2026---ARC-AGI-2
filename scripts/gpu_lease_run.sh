#!/usr/bin/env bash
# Run a GPU command on ngpu01 after the parent reserved a UUID.
# Does not call resource_queue.py (hostname must be prepost). Parent heartbeats.
set -euo pipefail
PROJECT=/home/scientists/gluz_d_s/kaggle/projects/arc-prize-2026-arc-agi-2
ENV="$PROJECT/envs/ngpu01/py3.11-cu124-unsloth-wip"
export PIP_CACHE_DIR="$PROJECT/cache/pip"
export TMPDIR="$PROJECT/cache/tmp"
export HF_HUB_CACHE="$PROJECT/cache/hf"
export TRANSFORMERS_CACHE="$PROJECT/cache/hf"
export TORCH_HOME="$PROJECT/cache/torch"
export XDG_CACHE_HOME="$PROJECT/cache/xdg"
export UNSLOTH_DISABLE_STATISTICS=1
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8

GPU_UUID=""
RUN_DIR=""
LOG_FILE=""
CMD=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --gpu-uuid) GPU_UUID="$2"; shift 2 ;;
    --run-dir) RUN_DIR="$2"; shift 2 ;;
    --) shift; CMD=("$@"); break ;;
    *) echo "unknown arg $1" >&2; exit 2 ;;
  esac
done
if [[ -z "$GPU_UUID" || -z "$RUN_DIR" || ${#CMD[@]} -eq 0 ]]; then
  echo "usage: gpu_lease_run.sh --gpu-uuid UUID --run-dir DIR -- cmd..." >&2
  exit 2
fi
mkdir -p "$RUN_DIR"
LOG_FILE="$RUN_DIR/job.log"
export CUDA_VISIBLE_DEVICES="$GPU_UUID"
{
  echo "host=$(hostname)"
  echo "date=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "cuda_visible=$CUDA_VISIBLE_DEVICES"
  nvidia-smi -L || true
  nvidia-smi --query-gpu=uuid,memory.used,memory.total,utilization.gpu --format=csv || true
} > "$RUN_DIR/preflight.txt"
nohup "$ENV/bin/python" "${CMD[@]}" >"$LOG_FILE" 2>&1 &
PID=$!
disown "$PID" || true
echo "$PID" > "$RUN_DIR/job.pid"
if [[ -r "/proc/$PID/stat" ]]; then
  awk '{print $22}' "/proc/$PID/stat" > "$RUN_DIR/job.start"
else
  date +%s > "$RUN_DIR/job.start"
fi
echo "$PID"
