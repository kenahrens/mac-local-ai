#!/usr/bin/env bash
# Start DS4 on demand. DS4 holds ~80GB resident once warmed, so it is NOT a
# safe always-on service alongside other large local models. Run this when
# you want the heavy model; pair with ds4-off.sh to free the memory.
set -euo pipefail
ROOT="$HOME/go/src/github.com/antirez/ds4"
if lsof -nP -iTCP:38011 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ds4 already running on :38011"; exit 0
fi
cd "$ROOT"
nohup ./ds4-server -m ds4flash.gguf --port 38011 --ctx 200000 \
  --kv-disk-dir "$HOME/.cache/ds4-kv" --kv-disk-space-mb 51200 --warm-weights \
  >> "$HOME/Library/Logs/ds4-server.log" 2>&1 &
echo "starting ds4-server (pid $!) on :38011, warming ~80GB of weights"
