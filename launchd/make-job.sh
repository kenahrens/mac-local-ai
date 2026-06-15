#!/usr/bin/env bash
# make-job.sh — create and load a macOS LaunchAgent for a local job.
#
# Usage:
#   make-job.sh --label <id> --interval <seconds> -- <command> [args...]
#   make-job.sh --label <id> --daily <HH:MM>      -- <command> [args...]
#
# Examples:
#   make-job.sh --label com.me.heartbeat --interval 900 -- /Users/me/bin/heartbeat.sh
#   make-job.sh --label com.me.morning   --daily 07:00  -- /Users/me/bin/morning.sh
#
# Why launchd and not cron: see README.md. Short version — launchd runs a job
# that was missed while the machine was asleep; cron silently skips it.

set -euo pipefail

LABEL="" INTERVAL="" DAILY=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --label) LABEL="$2"; shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    --daily) DAILY="$2"; shift 2 ;;
    --) shift; break ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

[[ -n "$LABEL" ]] || { echo "missing --label" >&2; exit 2; }
[[ $# -gt 0 ]] || { echo "missing command after --" >&2; exit 2; }
[[ -n "$INTERVAL" || -n "$DAILY" ]] || { echo "need --interval or --daily" >&2; exit 2; }

PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOGDIR="$HOME/.local/share/$LABEL"
mkdir -p "$LOGDIR" "$(dirname "$PLIST")"

# Build <ProgramArguments> from the remaining args.
PROG_ARGS=""
for arg in "$@"; do
  PROG_ARGS+="    <string>$arg</string>"$'\n'
done

# Build the schedule block.
if [[ -n "$INTERVAL" ]]; then
  SCHEDULE="  <key>StartInterval</key>
  <integer>$INTERVAL</integer>"
else
  HH="${DAILY%%:*}"; MM="${DAILY##*:}"
  SCHEDULE="  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>$((10#$HH))</integer>
    <key>Minute</key><integer>$((10#$MM))</integer>
  </dict>"
fi

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
$PROG_ARGS  </array>
$SCHEDULE
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StandardOutPath</key>
  <string>$LOGDIR/stdout.log</string>
  <key>StandardErrorPath</key>
  <string>$LOGDIR/stderr.log</string>
</dict>
</plist>
PLISTEOF

# Reload: boot out an existing copy, then bootstrap the new one.
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "loaded $LABEL"
echo "  plist: $PLIST"
echo "  logs:  $LOGDIR/{stdout,stderr}.log"
echo "remove with: launchctl bootout gui/$(id -u)/$LABEL && rm $PLIST"
