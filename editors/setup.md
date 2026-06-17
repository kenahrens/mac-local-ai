# Per-editor setup

Three things stay consistent across all four editors: the **AGENTS.md** instructions, the **MCP servers**, and the **local model endpoints**. Each editor keeps its own look, keymap, and native AI. Here's where each piece goes.

## The pieces

| Piece | Source of truth | How it spreads |
|---|---|---|
| Agent instructions | [`AGENTS.example.md`](AGENTS.example.md) → `AGENTS.md` in your repo | Cursor and Zed read `AGENTS.md` natively; for VS Code/VSCodium, Continue reads it too |
| MCP servers | [`mcp/servers.json`](mcp/servers.json) | `mcp/generate.py` emits each editor's format into `mcp/examples/` |
| Local models | [`continue/config.yaml`](continue/config.yaml) (VS Code family); native settings (Cursor, Zed) | point each at `http://localhost:38010/v1` (oMLX) etc. |

## Cursor

- **AI:** native (Cursor's agent). Point it at a local model under Settings → Models → add an OpenAI-compatible base URL (`http://localhost:38010/v1`).
- **MCP:** `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project). Root key `mcpServers` — copy `mcp/examples/cursor/mcp.json`.
- **Instructions:** reads `AGENTS.md`.

## VS Code

- **AI:** Copilot, or **Continue** for local models. Use `continue/config.yaml`.
- **MCP:** `.vscode/mcp.json`. Root key `servers`, each with `"type": "stdio"` — copy `mcp/examples/vscode/mcp.json`.
- **Quick install of Continue:** `./install-continue.sh` (installs Continue in VS Code and/or VSCodium, lays down `~/.continue/config.yaml` and `~/.continue/mcpServers/*.yaml` from the canonical sources, backs up any existing config before overwriting).

## VSCodium

- **AI:** **Continue** (open-vsx). Copilot is not available because it's a Microsoft-proprietary extension that won't install in VSCodium. This is the whole reason the AI layer is Continue here rather than Copilot.
- **MCP:** same as VS Code (`.vscode/mcp.json`, `servers`).
- **Quick install:** same `./install-continue.sh` covers VSCodium too.

## Zed

- **AI:** native (Zed's assistant). Supports OpenAI-compatible providers and Ollama — point it at the local endpoint.
- **MCP:** `settings.json` → `context_servers` — copy `mcp/examples/zed/settings-snippet.json`.
- **Instructions:** reads `AGENTS.md`.

## The gotchas

- **Three different root keys** for the same servers: `mcpServers` (Cursor), `servers` (VS Code/VSCodium), `context_servers` (Zed). You can't share one file — hence the generator.
- **VSCodium can't run Copilot.** If you want a consistent AI across VS Code *and* VSCodium, it can't be Copilot. Continue works in both.
- **`AGENTS.md` is the one thing that's nearly free** — it's becoming a cross-tool standard, so the instruction layer needs almost no per-editor work.
