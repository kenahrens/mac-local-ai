#!/usr/bin/env bash
# Install/refresh the ds4-server LaunchAgent.
#
# Renders com.antirez.ds4-server.plist.template into ~/Library/LaunchAgents/,
# then bootouts + bootstraps so the running server picks up the new spec.
# Idempotent — safe to re-run after changing the template or the env knobs.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="${DIR}/com.antirez.ds4-server.plist.template"

# Tunables — override via env before invoking.
DS4_REPO="${DS4_REPO:-${HOME}/go/src/github.com/antirez/ds4}"
DS4_PORT="${DS4_PORT:-38011}"
DS4_CTX="${DS4_CTX:-200000}"
DS4_KV_DIR="${DS4_KV_DIR:-${HOME}/.cache/ds4-kv}"
DS4_KV_MB="${DS4_KV_MB:-51200}"

# Sanity checks — fail loudly before we touch launchd.
if [ ! -x "${DS4_REPO}/ds4-server" ]; then
  echo "error: ds4-server binary not found at ${DS4_REPO}/ds4-server" >&2
  echo "       build it first: cd ${DS4_REPO} && make" >&2
  exit 1
fi
if [ ! -e "${DS4_REPO}/ds4flash.gguf" ]; then
  echo "error: model symlink not found at ${DS4_REPO}/ds4flash.gguf" >&2
  echo "       download a quant first: cd ${DS4_REPO} && ./download_model.sh q2-q4-imatrix" >&2
  exit 1
fi
mkdir -p "${DS4_KV_DIR}"
mkdir -p "${HOME}/Library/LaunchAgents"
mkdir -p "${HOME}/Library/Logs"

DEST="${HOME}/Library/LaunchAgents/com.antirez.ds4-server.plist"

# Render template. Using sed with | as delimiter so paths with / don't escape-hell.
sed \
  -e "s|__HOME__|${HOME}|g" \
  -e "s|__DS4_REPO__|${DS4_REPO}|g" \
  -e "s|__DS4_PORT__|${DS4_PORT}|g" \
  -e "s|__DS4_CTX__|${DS4_CTX}|g" \
  -e "s|__DS4_KV_DIR__|${DS4_KV_DIR}|g" \
  -e "s|__DS4_KV_MB__|${DS4_KV_MB}|g" \
  "${TEMPLATE}" > "${DEST}"

echo "wrote ${DEST}"

# Reload — bootout + bootstrap so launchd re-reads the plist. `kickstart -k`
# alone reuses the cached definition and ignores edits.
UID_NUM="$(id -u)"
DOMAIN="gui/${UID_NUM}"
SERVICE="${DOMAIN}/com.antirez.ds4-server"

if launchctl print "${SERVICE}" >/dev/null 2>&1; then
  echo "stopping existing service..."
  launchctl bootout "${SERVICE}" 2>/dev/null || true
  # bootout is async; give it a moment to release port 38011.
  for _ in 1 2 3 4 5; do
    if ! launchctl print "${SERVICE}" >/dev/null 2>&1; then break; fi
    sleep 1
  done
fi

echo "starting service..."
launchctl bootstrap "${DOMAIN}" "${DEST}"

# Confirm.
sleep 2
if launchctl print "${SERVICE}" >/dev/null 2>&1; then
  PID="$(launchctl list | awk '$3=="com.antirez.ds4-server"{print $1}')"
  echo "ds4-server running (pid ${PID:-unknown})"
  echo "logs: ${HOME}/Library/Logs/ds4-server.log"
  echo "endpoint: http://127.0.0.1:${DS4_PORT}/v1/models"
else
  echo "error: service failed to bootstrap; check ${HOME}/Library/Logs/ds4-server.log" >&2
  exit 1
fi
