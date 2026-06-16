#!/usr/bin/env bash
# Stop the on-demand DS4 server and free its memory.
set -euo pipefail
pkill -f 'ds4/ds4-server' && echo "stopped ds4-server" || echo "ds4-server was not running"
