#!/usr/bin/env bash
# setup.sh — one-shot install + model download for the qa-judge recipe.
#
# Idempotent. Re-running is safe; steps that are already done get skipped.
set -euo pipefail

MODEL="${MODEL:-mlx-community/gemma-4-12B-it-4bit}"
OMLX_HOME="${OMLX_HOME:-$HOME/.omlx}"
OMLX_PORT="${OMLX_PORT:-38010}"

say() { printf "\033[1;34m==>\033[0m %s\n" "$*"; }

# 1) Homebrew check.
if ! command -v brew >/dev/null 2>&1; then
  echo "error: Homebrew not found. Install from https://brew.sh first." >&2
  exit 2
fi

# 2) Trust the jundot/omlx tap. Newer Homebrew rejects untrusted third-party
#    formulae; this is idempotent so re-running just re-affirms trust.
say "trusting jundot/omlx tap"
brew trust jundot/omlx 2>/dev/null || true

# 3) Install oMLX if missing.
if ! brew list omlx >/dev/null 2>&1; then
  say "installing oMLX"
  brew install jundot/omlx/omlx
else
  say "oMLX already installed"
fi

# 4) Start oMLX as a Homebrew service so it auto-runs at login and restarts on crash.
say "starting oMLX as a Homebrew service"
brew services start omlx >/dev/null

# 5) Wait for the API to come up before downloading. Cold start can take a beat.
say "waiting for oMLX to listen on :$OMLX_PORT"
for _ in $(seq 1 60); do
  if curl -sf --max-time 1 "http://127.0.0.1:$OMLX_PORT/v1/models" >/dev/null; then
    break
  fi
  sleep 1
done

# 6) Download the model. Skip if already present.
DEST="$OMLX_HOME/models/$MODEL"
if [ -d "$DEST" ] && [ -n "$(ls -A "$DEST" 2>/dev/null)" ]; then
  say "model already downloaded: $MODEL"
else
  say "downloading $MODEL (about 6 GB, takes a few minutes on a fresh connection)"
  PYTHON="/opt/homebrew/opt/omlx/libexec/bin/python"
  mkdir -p "$DEST"
  "$PYTHON" - "$MODEL" "$DEST" <<'PY'
import sys
from huggingface_hub import snapshot_download
model_id, dest = sys.argv[1:3]
print(snapshot_download(repo_id=model_id, local_dir=dest))
PY
fi

# 7) Sanity check: model should be listed by oMLX once it scans its model dir.
say "models oMLX can serve:"
curl -s "http://127.0.0.1:$OMLX_PORT/v1/models" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for m in d.get('data', []):
    print('   -', m['id'])
"

cat <<EOF

Setup done. Try the recipe:

  ./judge.py            # send sample-drift.json at the model, see verdicts
  ./bench.py            # 5 runs, report tokens-per-second

EOF
