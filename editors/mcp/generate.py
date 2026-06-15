#!/usr/bin/env python3
"""Emit each editor's MCP config from the canonical servers.json.

Cursor uses `mcpServers`, VS Code / VSCodium use `servers` (with a `type`),
Zed uses `context_servers`, and Continue wants one YAML file per server.
Same servers, four shapes. Edit servers.json, run this, copy what you need.
"""
import json, pathlib

ROOT = pathlib.Path(__file__).parent
servers = json.loads((ROOT / "servers.json").read_text())["mcpServers"]
out = ROOT / "examples"

def write_json(rel, obj):
    p = out / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2) + "\n")
    print("wrote", p.relative_to(ROOT))

# Cursor — .cursor/mcp.json (root key: mcpServers)
write_json("cursor/mcp.json", {"mcpServers": servers})

# VS Code / VSCodium — .vscode/mcp.json (root key: servers, needs a type)
vscode = {name: {"type": "stdio", **cfg} for name, cfg in servers.items()}
write_json("vscode/mcp.json", {"servers": vscode})

# Zed — settings.json snippet (root key: context_servers)
zed = {name: {"source": "custom", **cfg} for name, cfg in servers.items()}
write_json("zed/settings-snippet.json", {"context_servers": zed})

# Continue — one YAML file per server under .continue/mcpServers/
cont = out / "continue" / "mcpServers"
cont.mkdir(parents=True, exist_ok=True)
for name, cfg in servers.items():
    lines = [f"name: {name}", f"command: {cfg['command']}", "args:"]
    lines += [f"  - {a}" for a in cfg["args"]]
    (cont / f"{name}.yaml").write_text("\n".join(lines) + "\n")
    print("wrote", (cont / f"{name}.yaml").relative_to(ROOT))
