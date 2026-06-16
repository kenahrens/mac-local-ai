#!/usr/bin/env bash
set -euo pipefail

OMLX_HOME="${OMLX_HOME:-$HOME/.omlx}"
OMLX_PORT="${OMLX_PORT:-38010}"
OMLX_MODEL_DIR="${OMLX_MODEL_DIR:-$OMLX_HOME/models}"
OMLX_SSD_CACHE_DIR="${OMLX_SSD_CACHE_DIR:-$OMLX_HOME/cache}"
OMLX_HOT_CACHE_MAX_SIZE="${OMLX_HOT_CACHE_MAX_SIZE:-20GB}"
OMLX_MAX_CONCURRENT_REQUESTS="${OMLX_MAX_CONCURRENT_REQUESTS:-1}"

exec /opt/homebrew/opt/omlx/bin/omlx serve \
  --model-dir "$OMLX_MODEL_DIR" \
  --port "$OMLX_PORT" \
  --hot-cache-max-size "$OMLX_HOT_CACHE_MAX_SIZE" \
  --max-concurrent-requests "$OMLX_MAX_CONCURRENT_REQUESTS" \
  --paged-ssd-cache-dir "$OMLX_SSD_CACHE_DIR"
