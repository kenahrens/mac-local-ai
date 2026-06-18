# Per-editor setup

Three things stay consistent across all four editors: the **AGENTS.md** instructions, the **MCP servers**, and the **local model endpoints**. Each editor keeps its own look, keymap, and native AI. Here's where each piece goes.

## The pieces

| Piece | Source of truth | How it spreads |
|---|---|---|
| Agent instructions | [`AGENTS.example.md`](AGENTS.example.md) → `AGENTS.md` in your repo | Cursor and Zed read `AGENTS.md` natively |
| MCP servers | [`mcp/servers.json`](mcp/servers.json) | `mcp/generate.py` emits each editor's format into `mcp/examples/` |
| Local models | native settings (Cursor, Zed); open question for VS Code / VSCodium | point each at `http://localhost:38010/v1` (oMLX) etc. |

## Cursor

- **AI:** native (Cursor's agent). Point it at a local model under Settings → Models → add an OpenAI-compatible base URL (`http://localhost:38010/v1`).
- **MCP:** `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project). Root key `mcpServers`. Copy `mcp/examples/cursor/mcp.json`.
- **Instructions:** reads `AGENTS.md`.

## VS Code

- **AI:** Copilot if you're a paying user. For local-model / OSS workflows, the right extension is an open question. Continue had reliability issues; Cline and other extensions are worth trying. See [open questions](#open-questions) below.
- **MCP:** `.vscode/mcp.json`. Root key `servers`, each with `"type": "stdio"`. Copy `mcp/examples/vscode/mcp.json`.

## VSCodium

- **AI:** same open question as VS Code, and worse because Copilot isn't available at all. VSCodium is the editor that most needs an OSS AI extension picked.
- **MCP:** same as VS Code (`.vscode/mcp.json`, `servers`).

## Zed

- **AI:** native (Zed's assistant). Supports OpenAI-compatible providers and Ollama. Point it at the local endpoint.
- **MCP:** `settings.json` under `context_servers`. Copy `mcp/examples/zed/settings-snippet.json`.
- **Instructions:** reads `AGENTS.md`.

## The gotchas

- **Three different root keys** for the same servers: `mcpServers` (Cursor), `servers` (VS Code/VSCodium), `context_servers` (Zed). You can't share one file, hence the generator.
- **VSCodium can't run Copilot.** It's a Microsoft-proprietary extension and won't install on open-vsx. If you want consistent AI in VS Code *and* VSCodium, you need something on open-vsx.
- **`AGENTS.md` is the one thing that's nearly free.** It's becoming a cross-tool standard, so the instruction layer needs almost no per-editor work.

## Open questions

- **Which AI extension** for VS Code / VSCodium? Continue was tried and had reliability issues with MCP servers and indexing on Mac. Cline (`saoudrizwan.claude-dev`) is the next candidate and is on open-vsx. Will revisit and update this README once one is validated end-to-end.
