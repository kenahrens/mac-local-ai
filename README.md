# mac-local-ai

The AI setup I run locally on a Mac. Scripts and notes, not a product. It works for me on an M5 with 128GB of RAM. No promises it works for you, and there's no support.

Most of this is glue around other people's open source. The engines are theirs. What's here is how I wire them up and the things I had to figure out.

## What's in here

- **[`omlx/`](omlx/)** — running [oMLX](https://github.com/jundot/omlx) as a local inference server, and the flags that mattered.
- **[`ds4/`](ds4/)** — running [antirez's DeepSeek build](https://github.com/antirez/ds4) as a LaunchAgent.
- **[`short/`](short/)** — turning a long screen recording into vertical YouTube Shorts, using a local LLM to pick and judge the clips.
- **[`launchd/`](launchd/)** — scheduling local jobs with launchd instead of cron, and why.
- **[`editors/`](editors/)** — keeping Zed, VSCodium, VS Code, and Cursor consistent on `AGENTS.md`, MCP servers, and the local model endpoints.
- **[`tools/`](tools/)** — small standalone scripts: an AI-writing-tells linter, an ephemeral local-model chat, and Whisper transcription.

## What I run (M5, 128GB)

- **[oMLX](https://github.com/jundot/omlx)** — OpenAI-compatible server for MLX models. I picked it over `mlx_lm.server` and FastMLX for one reason: a paged SSD KV-cache. A repeated prompt prefix restores from disk instead of recomputing, so time-to-first-token on long contexts drops from tens of seconds to a couple. Default model is a 27B Qwen; there's a 0.5B around for smoke tests.
- **[VoiceInk](https://github.com/Beingpax/VoiceInk)** — on-device voice-to-text (whisper.cpp, large-v3). On a machine this capable there's no reason to send my microphone to someone's cloud.
- **[ds4](https://github.com/antirez/ds4)** — antirez's local DeepSeek build, for a second opinion on coding. It defaults to a thinking mode that only streams reasoning tokens, so a naive client looks like it hung. Ask for the non-thinking variant.

## License

MIT. See [LICENSE](LICENSE).
