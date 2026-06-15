# mac-local-ai

The local AI setup I run on a Mac. Recipes and notes, not a product. It works for me on an M5 with 128GB of RAM; your mileage will vary, and there's no support. If it saves you an afternoon, great.

Most of this is thin glue around other people's open source. The interesting engines are theirs; what's here is the wiring and the notes on what actually mattered.

## What's in here

- **[`omlx/`](omlx/)** — scripts to run [oMLX](https://github.com/jundot/omlx) as an always-on local inference server, plus the flag tuning that mattered.
- **[`short/`](short/)** — a tool that turns a long screen recording into vertical YouTube Shorts using a local LLM to pick and judge the clips.
- **[`launchd/`](launchd/)** — a small helper for scheduling local jobs with launchd instead of cron, and why.

## What I run (M5, 128GB)

| Tool | What it does | Notes |
|---|---|---|
| **[oMLX](https://github.com/jundot/omlx)** | OpenAI-compatible inference server for MLX models | The reason I picked it over `mlx_lm.server`/FastMLX: a paged SSD KV-cache. A returning prompt prefix restores from disk instead of recomputing, so time-to-first-token on long contexts drops from tens of seconds to a couple. That's the whole game for coding agents. |
| **[VoiceInk](https://github.com/Beingpax/VoiceInk)** | On-device voice-to-text (whisper.cpp, large-v3) | Runs entirely local. On a capable Mac there's no reason to ship your microphone to someone's cloud. |
| **ds4** | A local DeepSeek build (OpenAI-compatible) | Second opinion for coding tasks. Gotcha: it defaults to a thinking mode that only streams `reasoning_content`, so a naive client shows a blank response. Ask for the non-thinking variant. |

### oMLX models I keep around (port 38010)

| Model | Role | Speed |
|---|---|---|
| `Qwen3.6-27B-4bit` | default, complex reasoning | ~30 tok/s |
| `Nemotron-30B` | faster alternative | untimed |
| `Gemma-31B` | tool-loop work | untimed |
| `Qwen2.5-0.5B` | smoke test only | fast |

(Only the default is carefully benchmarked. The rest are honest "I haven't timed it" entries.)

## The one idea worth stealing

As a task matures from "poke at it in a chat window" to "runs on a timer," it should also migrate off rented frontier models and onto hardware you already own. `short` is an example: the script runs ffmpeg and Whisper deterministically and only calls the LLM for *judgment* (which clips, where to crop). That inversion — script drives, model judges — is a big token saver and more reliable than handing an agent a pile of tools.

## License

MIT. See [LICENSE](LICENSE).
