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

### AWS Bedrock in Zed

Use Zed's built-in agent with the native Bedrock provider. Configure an existing AWS SSO profile, then preview and apply the settings merge from this repository's root:

```sh
aws sso login --profile my-bedrock-profile
python3 editors/zed/configure-bedrock.py --profile my-bedrock-profile --region us-east-1
python3 editors/zed/configure-bedrock.py --profile my-bedrock-profile --region us-east-1 --apply
```

The default model is `gpt-5.6-sol`, Zed's internal ID for the Bedrock model `openai.gpt-5.6-sol`; override it with `--model` for a model supported by your Zed version and available to your AWS account in the selected region. The helper sets the main agent, inline assistant, commit messages, thread summaries, compaction, and subagents to the same Bedrock model and adds it to favorites. Existing local providers, external agents, MCP connections, and permissions are preserved. Edit prediction has separate provider settings and is not changed by this helper.

The helper merges into `~/.config/zed/settings.json` without copying credentials. Use `--settings PATH` to preview or apply to another file. It accepts strict JSON and refuses JSONC comments or trailing commas without changing the file. The MCP installers merge their own entries and preserve these model settings.

Zed uses `amazon-bedrock` in agent model selections and `bedrock` under `language_models`; these are different settings keys. Current MCP entries omit the retired `source` property. If Zed shows an outdated-settings warning for an older entry, use its migration action or remove that entry's obsolete `source` property.

Zed reloads settings automatically. Open a new **Zed Agent** thread and choose the model under **Amazon Bedrock** in the picker. Existing OpenCode, Codex, Claude, and other external-agent threads keep their own provider configuration. Verify a short prompt in an empty folder before using customer files. An initial successful request does not verify renewal after SSO expiry.

The AWS SDK renews temporary credentials while the underlying SSO login remains valid. When that login expires, run `aws sso login --profile my-bedrock-profile` again. If Zed retains an authentication error after successful login, retry the prompt and restart Zed if necessary; do not replace SSO with copied temporary credentials. See [Zed's Bedrock documentation](https://zed.dev/docs/ai/use-a-gateway#amazon-bedrock) and [AWS's SSO refresh lifecycle](https://docs.aws.amazon.com/sdkref/latest/guide/understanding-sso.html).

## The gotchas

- **Three different root keys** for the same servers: `mcpServers` (Cursor), `servers` (VS Code/VSCodium), `context_servers` (Zed). You can't share one file, hence the generator.
- **VSCodium can't run Copilot.** It's a Microsoft-proprietary extension and won't install on open-vsx. If you want consistent AI in VS Code *and* VSCodium, you need something on open-vsx.
- **`AGENTS.md` is the one thing that's nearly free.** It's becoming a cross-tool standard, so the instruction layer needs almost no per-editor work.

## Open questions

- **Which AI extension** for VS Code / VSCodium? Continue was tried and had reliability issues with MCP servers and indexing on Mac. Cline (`saoudrizwan.claude-dev`) is the next candidate and is on open-vsx. Will revisit and update this README once one is validated end-to-end.
