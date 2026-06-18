# editors

I switch between Zed, VSCodium, VS Code, and Cursor and haven't picked a daily driver. This keeps the parts that should be the same actually the same, without making the editors identical. Notes and configs, not a product.

What stays consistent: the **agent instructions** (`AGENTS.md`), the **MCP servers**, and the **local model endpoints**. What stays native: each editor's look, keymap, and its own AI. Cursor and Zed have their own AI built in. For VS Code and VSCodium, the open-source AI extension is an open question (Continue was tried and was unreliable; Cline and others are worth trying).

## Layout

- [`mcp/servers.json`](mcp/servers.json): one canonical MCP roster. Run `mcp/generate.py` to emit each editor's format into `mcp/examples/`. Cursor, VS Code, and Zed each want a different root key for the same servers.
- [`AGENTS.example.md`](AGENTS.example.md): the shared instructions file. Cursor and Zed read it natively.
- [`setup.md`](setup.md): where every config goes, per editor, and the gotchas.

## The two things that trip people up

- **One server, three config shapes.** Cursor wants `mcpServers`, VS Code/VSCodium want `servers` (with a `type`), Zed wants `context_servers`. You can't share one file, so `servers.json` + the generator is the source of truth.
- **VSCodium can't run Copilot.** It's a Microsoft-proprietary extension and won't install on open-vsx. If you want the same AI in VS Code *and* VSCodium, you need a third-party extension that's on open-vsx. The right answer here is open.

