#!/usr/bin/env bash
# A toy job: print a timestamp. launchd captures stdout to the job's log.
set -euo pipefail
echo "hello from launchd at $(date '+%Y-%m-%d %H:%M:%S')"
