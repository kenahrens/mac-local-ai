# tools

Small standalone scripts that lean on the local AI stack.

| Tool | What it does |
|---|---|
| `check-ai-tells.sh <file>` | Static linter for AI-writing tells — em-dash overuse, rule-of-three, title-case headings, section-divider rules, and a hook for your own banned terms. Exit 0 = clean, 1 = issues found. No model needed; it's just regex. |
| `privatechat.mjs` | An ephemeral, network-isolated chat with a **local** model (default oMLX gemma). History lives in RAM, nothing is written to disk, and it never opens any other tool's database. A disposable private session. |
| `transcribe.sh <audio> [out-dir]` | Transcribe an audio file with local Whisper to a `.txt`. |

All three run offline against your own machine. `privatechat` and `check-ai-tells` assume an OpenAI-compatible endpoint (see [`../omlx/`](../omlx/)); `transcribe` needs `whisper` installed.
