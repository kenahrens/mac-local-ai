#!/usr/bin/env bash
set -euo pipefail

LABEL="homebrew.mxcl.omlx"
PORT="${OMLX_PORT:-38010}"

echo "LaunchAgent:"
launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null || echo "  not loaded"

echo
echo "Port $PORT:"
lsof -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || echo "  not listening"

echo
echo "Models:"
curl -sS "http://127.0.0.1:$PORT/v1/models" 2>/dev/null || echo "  API not responding"
echo
