#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: $0 <huggingface-model-id> [revision]" >&2
  echo "example: $0 mlx-community/Qwen2.5-0.5B-Instruct-4bit" >&2
  exit 2
fi

MODEL_ID="$1"
REVISION="${2:-}"
OMLX_HOME="${OMLX_HOME:-$HOME/.omlx}"
OMLX_MODEL_DIR="${OMLX_MODEL_DIR:-$OMLX_HOME/models}"
DEST="$OMLX_MODEL_DIR/$MODEL_ID"
PYTHON="/opt/homebrew/opt/omlx/libexec/bin/python"

mkdir -p "$DEST"

if [[ -n "$REVISION" ]]; then
  exec "$PYTHON" - "$MODEL_ID" "$DEST" "$REVISION" <<'PY'
import sys
from huggingface_hub import snapshot_download

model_id, dest, revision = sys.argv[1:4]
path = snapshot_download(repo_id=model_id, revision=revision, local_dir=dest)
print(path)
PY
else
  exec "$PYTHON" - "$MODEL_ID" "$DEST" <<'PY'
import sys
from huggingface_hub import snapshot_download

model_id, dest = sys.argv[1:3]
path = snapshot_download(repo_id=model_id, local_dir=dest)
print(path)
PY
fi
