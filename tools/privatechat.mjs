#!/usr/bin/env node
// privatechat.mjs — ephemeral, network-isolated chat with a LOCAL model.
//
// A disposable "private session": talks straight to the local omlx endpoint
// (gemma-4 by default) over loopback, keeps all history in RAM, and writes
// NOTHING to disk. It never opens opencode's database, so there is nothing to
// clean up and your real opencode store is provably untouched.
//
// Privacy is enforced two ways:
//   1. By construction — the only socket it opens is http://127.0.0.1:<port>.
//      No MCP, no plugins, no telemetry, no persistence.
//   2. By sandbox — it re-execs itself under macOS `sandbox-exec` with a
//      profile that DENIES all outbound network except loopback (DNS included).
//      Even a bug can't phone home.
//
// Usage:
//   privatechat.mjs                      # interactive REPL, gemma-4
//   privatechat.mjs -m gemma-4-e4b-it-4bit
//   privatechat.mjs "one-shot prompt"    # answer once, print, exit
//
// Flags:
//   -m, --model <name>   omlx model id (default: gemma-4-31b-it-4bit)
//       --port <n>       omlx port (default: $OMLX_PORT or 38010)
//       --system <text>  system prompt
//       --no-sandbox     skip the sandbox-exec network lockdown (debug only)
//   -h, --help
//
// In-REPL commands: /reset  /system <text>  /model <name>  /help  /exit
//
// Exit codes: 0 ok, 1 usage error, 2 omlx/connection error.

import { spawnSync } from "child_process";
import { fileURLToPath } from "url";
import { createInterface } from "readline";

const DEFAULT_MODEL = "gemma-4-31b-it-4bit";

function parseArgs(argv) {
  const out = { positional: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    switch (a) {
      case "-m":
      case "--model":      out.model = argv[++i]; break;
      case "--port":       out.port = argv[++i]; break;
      case "--system":     out.system = argv[++i]; break;
      case "--no-sandbox": out.noSandbox = true; break;
      case "-h":
      case "--help":       out.help = true; break;
      default:             out.positional.push(a);
    }
  }
  return out;
}

function help() {
  process.stdout.write(
`privatechat — ephemeral, network-isolated chat with a local model.

  privatechat                       interactive REPL (gemma-4)
  privatechat -m gemma-4-e4b-it-4bit
  privatechat "summarize this idea"  one-shot, prints answer, exits

Flags:
  -m, --model <name>   omlx model id (default: ${DEFAULT_MODEL})
      --port <n>       omlx port (default: $OMLX_PORT or 38010)
      --system <text>  system prompt
      --no-sandbox     skip sandbox-exec network lockdown (debug only)
  -h, --help

In-REPL: /reset  /system <text>  /model <name>  /help  /exit

Nothing is written to disk. Network is locked to loopback only.
`);
}

// macOS Seatbelt profile: allow everything by default, then deny all outbound
// network and re-allow only loopback (so we can reach omlx at 127.0.0.1).
// DNS resolution to external resolvers is therefore blocked too.
const SANDBOX_PROFILE =
  '(version 1)' +
  '(allow default)' +
  '(deny network-outbound)' +
  '(allow network-outbound (remote ip "localhost:*"))';

// Re-exec under sandbox-exec unless already sandboxed or opted out.
function ensureSandboxed(rawArgv) {
  if (process.env.PRIVATECHAT_SANDBOXED === "1") return;
  if (rawArgv.includes("--no-sandbox")) return;
  if (process.platform !== "darwin") return; // sandbox-exec is macOS-only
  const self = fileURLToPath(import.meta.url);
  const r = spawnSync(
    "sandbox-exec",
    ["-p", SANDBOX_PROFILE, process.execPath, self, ...rawArgv],
    { stdio: "inherit", env: { ...process.env, PRIVATECHAT_SANDBOXED: "1" } }
  );
  if (r.error) {
    process.stderr.write(`privatechat: could not sandbox (${r.error.message}); ` +
      `re-run with --no-sandbox to bypass.\n`);
    process.exit(2);
  }
  process.exit(r.status ?? 0);
}

// Stream a chat completion from omlx; return the assembled assistant text.
async function complete(baseURL, model, messages, onDelta) {
  let res;
  try {
    res = await fetch(`${baseURL}/v1/chat/completions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model, messages, stream: true }),
    });
  } catch (e) {
    throw new Error(`cannot reach omlx at ${baseURL} (${e.cause?.code || e.message}). ` +
      `Is it running?  ~/…/speedstack/scripts/start-omlx.sh`);
  }
  if (!res.ok) {
    throw new Error(`omlx returned HTTP ${res.status}: ${(await res.text()).slice(0, 200)}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "", full = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let nl;
    while ((nl = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (!line.startsWith("data:")) continue;
      const data = line.slice(5).trim();
      if (data === "[DONE]") continue;
      try {
        const delta = JSON.parse(data).choices?.[0]?.delta?.content;
        if (delta) { full += delta; onDelta(delta); }
      } catch { /* ignore keep-alive / partial */ }
    }
  }
  return full;
}

async function main() {
  ensureSandboxed(process.argv.slice(2));

  const args = parseArgs(process.argv.slice(2));
  if (args.help) { help(); process.exit(0); }

  const model = args.model || DEFAULT_MODEL;
  const port = args.port || process.env.OMLX_PORT || "38010";
  const baseURL = `http://127.0.0.1:${port}`;
  const messages = [];
  if (args.system) messages.push({ role: "system", content: args.system });

  // One-shot mode: prompt given on the command line.
  if (args.positional.length) {
    messages.push({ role: "user", content: args.positional.join(" ") });
    try {
      await complete(baseURL, model, messages, (d) => process.stdout.write(d));
      process.stdout.write("\n");
    } catch (e) { process.stderr.write(`\nprivatechat: ${e.message}\n`); process.exit(2); }
    return;
  }

  // Interactive REPL.
  const lock = args.noSandbox ? "⚠ net:UNRESTRICTED" : "🔒 net:loopback-only";
  process.stdout.write(`privatechat · ${model} · ${lock} · 🗑 ephemeral (nothing saved)\n`);
  process.stdout.write(`type /help for commands, /exit to quit\n`);

  const rl = createInterface({ input: process.stdin, output: process.stdout });
  const tty = process.stdin.isTTY;
  if (tty) rl.setPrompt("you> "), rl.prompt();

  // Sequential line processing — `for await` waits for each turn's completion
  // before reading the next line, so EOF (Ctrl-D / piped heredoc) never
  // truncates an in-flight response.
  for await (const line of rl) {
    const t = line.trim();
    if (t === "/exit" || t === "/quit") break;
    if (t === "/help") { process.stdout.write("/reset  /system <text>  /model <name>  /help  /exit\n"); if (tty) rl.prompt(); continue; }
    if (t === "/reset") {
      messages.length = 0;
      if (args.system) messages.push({ role: "system", content: args.system });
      process.stdout.write("(history cleared)\n"); if (tty) rl.prompt(); continue;
    }
    if (t.startsWith("/system ")) {
      const sys = t.slice(8);
      const i = messages.findIndex((m) => m.role === "system");
      if (i >= 0) messages[i].content = sys; else messages.unshift({ role: "system", content: sys });
      process.stdout.write("(system prompt set)\n"); if (tty) rl.prompt(); continue;
    }
    if (t.startsWith("/model ")) { args.model = t.slice(7); process.stdout.write(`(model → ${args.model})\n`); if (tty) rl.prompt(); continue; }
    if (!t) { if (tty) rl.prompt(); continue; }

    messages.push({ role: "user", content: t });
    process.stdout.write("gemma> ");
    try {
      const reply = await complete(baseURL, args.model || model, messages, (d) => process.stdout.write(d));
      messages.push({ role: "assistant", content: reply });
      process.stdout.write("\n");
    } catch (e) {
      messages.pop(); // drop the user turn we couldn't answer
      process.stdout.write(`\n[error] ${e.message}\n`);
    }
    if (tty) rl.prompt();
  }
  rl.close();
  process.stdout.write("\n(session discarded — nothing was written to disk)\n");
}

main();
