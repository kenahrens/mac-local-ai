#!/usr/bin/env bash
# install-continue.sh — set up Continue (https://continue.dev) in VS Code and/or
# VSCodium. Continue is the AI layer when you want a consistent setup across
# both editors, because Copilot doesn't work on VSCodium.
#
# Idempotent: re-running just re-affirms. Backs up any existing config.yaml
# before overwriting.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_SRC="$DIR/continue/config.yaml"
MCP_ROSTER="$DIR/mcp/servers.json"
CONTINUE_HOME="$HOME/.continue"

say() { printf "\033[1;34m==>\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!!\033[0m %s\n" "$*" >&2; }

[ -f "$CONFIG_SRC" ] || { echo "error: $CONFIG_SRC missing" >&2; exit 2; }

# 1) Install the extension in each editor that's present. Continue's id is the
#    same in both marketplaces (VS Code marketplace and open-vsx, which is what
#    VSCodium uses).
EXT="Continue.continue"
INSTALLED_IN=()
if command -v code >/dev/null 2>&1; then
  if code --list-extensions 2>/dev/null | grep -qi "^${EXT}$"; then
    say "VS Code: Continue already installed"
  else
    say "VS Code: installing Continue"
    code --install-extension "$EXT" >/dev/null
  fi
  INSTALLED_IN+=("VS Code")
else
  warn "VS Code CLI ('code') not on PATH, skipping"
fi
if command -v codium >/dev/null 2>&1; then
  if codium --list-extensions 2>/dev/null | grep -qi "^${EXT}$"; then
    say "VSCodium: Continue already installed"
  else
    say "VSCodium: installing Continue"
    codium --install-extension "$EXT" >/dev/null
  fi
  INSTALLED_IN+=("VSCodium")
else
  warn "VSCodium CLI ('codium') not on PATH, skipping"
fi
if [ "${#INSTALLED_IN[@]}" -eq 0 ]; then
  echo "error: neither 'code' nor 'codium' found, nothing to install Continue into" >&2
  exit 2
fi

# 2) Write the canonical config to ~/.continue/config.yaml, backing up any
#    existing one so a re-run can't silently lose a custom edit.
mkdir -p "$CONTINUE_HOME"
DEST="$CONTINUE_HOME/config.yaml"
if [ -f "$DEST" ]; then
  if cmp -s "$CONFIG_SRC" "$DEST"; then
    say "Continue config already matches the canonical version, no change"
  else
    BAK="$DEST.bak-$(/bin/date +%Y%m%d-%H%M%S)"
    say "backing up existing config to $BAK"
    cp "$DEST" "$BAK"
    cp "$CONFIG_SRC" "$DEST"
    say "wrote $DEST"
  fi
else
  cp "$CONFIG_SRC" "$DEST"
  say "wrote $DEST"
fi

# 3) Lay down the MCP servers from the canonical roster. Continue reads one
#    YAML per server from ~/.continue/mcpServers/.
if [ -f "$MCP_ROSTER" ]; then
  mkdir -p "$CONTINUE_HOME/mcpServers"
  python3 - "$MCP_ROSTER" "$CONTINUE_HOME/mcpServers" <<'PY'
import json, os, sys
roster_path, out_dir = sys.argv[1], sys.argv[2]
with open(roster_path) as f:
    roster = json.load(f)
servers = roster.get("mcpServers", {})
written = []
for name, spec in servers.items():
    cmd = spec.get("command")
    args = spec.get("args", [])
    if not cmd:
        continue
    args_yaml = "\n".join(f"      - {repr(a)}" for a in args)
    body = f"""name: {name}
version: 0.0.1
schema: v1
mcpServers:
  - name: {name}
    command: {cmd}
    args:
{args_yaml}
"""
    path = os.path.join(out_dir, f"{name}.yaml")
    with open(path, "w") as f:
        f.write(body)
    written.append(name)
print("  wrote MCP servers:", ", ".join(written))
PY
  say "MCP servers under $CONTINUE_HOME/mcpServers/"
fi

# 4) Sanity report.
echo
say "done. Continue installed in: ${INSTALLED_IN[*]}"
say "config: $DEST"
[ -d "$CONTINUE_HOME/mcpServers" ] && say "MCP: $(ls "$CONTINUE_HOME/mcpServers"/*.yaml 2>/dev/null | wc -l | tr -d ' ') server file(s) under $CONTINUE_HOME/mcpServers/"
cat <<EOF

Next steps (manual, by design):

- Open VS Code or VSCodium. Continue's icon appears in the sidebar.
- The first time Continue tries to use the Claude cloud fallback, it'll prompt
  for the ANTHROPIC_API_KEY secret. Paste it once; Continue stores it locally.
- Confirm Continue can see the local models by opening its chat panel and
  picking "oMLX Gemma 31B (local)" from the model menu. Send a hello message;
  you should get a reply within a second or two.

EOF
